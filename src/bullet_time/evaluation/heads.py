"""Matched frozen readouts and strictly framewise supervised controls."""
import torch
from torch import nn
from bullet_time.models.video import encode_video


class AttentionHead(nn.Module):
    def __init__(self, input_width, task, *, width=256, depth=2, heads=4, classes=174):
        super().__init__()
        if task not in ('collision','order','tracking','ssv2'): raise ValueError('unknown readout task')
        self.task=task
        self.project=nn.Linear(input_width,width)
        self.query=nn.Parameter(torch.zeros(1,1,width))
        self.coordinates=nn.Linear(4 if task in ('collision','order') else 2,width) if task!='ssv2' else None
        self.reference_segment=nn.Parameter(torch.zeros(1,1,width))
        self.layers=nn.ModuleList([nn.TransformerDecoderLayer(width,heads,dim_feedforward=4*width,
            dropout=0.0,activation='gelu',batch_first=True,norm_first=True) for _ in range(depth)])
        self.norm=nn.LayerNorm(width)
        self.output=nn.Linear(width,3 if task=='tracking' else classes if task=='ssv2' else 1)

    def forward(self, tokens, query_points=None, reference_tokens=None, reference_point=None):
        memory=self.project(tokens)
        query=self.query.expand(tokens.shape[0],-1,-1)
        if self.task in ('collision','order'):
            if query_points is None or query_points.shape!=(tokens.shape[0],2,2): raise ValueError('forecast requires two points')
            query=query+self.coordinates(query_points.flatten(1))[:,None]
        if self.task=='tracking':
            if reference_tokens is None or reference_point is None or reference_point.shape!=(tokens.shape[0],2):
                raise ValueError('tracking requires past reference features and point')
            memory=torch.cat([memory,self.project(reference_tokens)+self.reference_segment],1)
            query=query+self.coordinates(reference_point)[:,None]
        for layer in self.layers: query=layer(query,memory)
        return self.output(self.norm(query[:,0]))


class FrozenReadout(nn.Module):
    def __init__(self, backbone, task, **head_kwargs):
        super().__init__();self.backbone=backbone;self.task=task
        self.backbone.requires_grad_(False).eval()
        self.head=AttentionHead(backbone.bt_config.encoder_width,task,**head_kwargs)

    def train(self, mode=True):
        super().train(mode);self.backbone.eval();return self

    def forward(self, video, query_points=None, reference=None, reference_point=None):
        with torch.no_grad():
            features=encode_video(self.backbone,video)
            reference_features=encode_video(self.backbone,reference) if reference is not None else None
        return self.head(features,query_points,reference_features,reference_point)


class FrameEncoder(nn.Module):
    """Image-MAE encoder applied independently; no context or temporal positions."""
    def __init__(self, image_backbone):
        super().__init__()
        if image_backbone.bt_config.frames!=1: raise ValueError('requires an actual image backbone')
        self.backbone=image_backbone
        # Decoder/projection/mask token are not part of the image representation.
        if hasattr(image_backbone,'decoder'): image_backbone.decoder.requires_grad_(False)
        if hasattr(image_backbone,'encoder_to_decoder'): image_backbone.encoder_to_decoder.requires_grad_(False)
        if hasattr(image_backbone,'mask_token'): image_backbone.mask_token.requires_grad_(False)
        self.width=image_backbone.bt_config.encoder_width

    def forward(self, video):
        b,c,t,h,w=video.shape
        frames=video.permute(0,2,1,3,4).reshape(b*t,c,1,h,w)
        features=encode_video(self.backbone,frames)
        return features.reshape(b,t,features.shape[1],self.width)


class DiagnosticModel(nn.Module):
    """One shared image architecture across sequence/final/bag/current controls."""
    def __init__(self, frame_encoder, task, mode='sequence', **head_kwargs):
        super().__init__()
        if mode not in ('sequence','final_frame','bag','current_frame'): raise ValueError('unknown mode')
        if mode=='current_frame' and task!='tracking' or mode in ('final_frame','bag') and task not in ('collision','order'):
            raise ValueError('mode/task mismatch')
        self.encoder=frame_encoder;self.task=task;self.mode=mode
        width=frame_encoder.width
        self.head=AttentionHead(width,task,**head_kwargs)
        # Fixed temporal encoding only on the ordered sequence branch.
        position=torch.arange(16,dtype=torch.float32)[:,None]
        frequency=10000**(-torch.arange(width,dtype=torch.float32)[None,:]/width)
        self.register_buffer('time_position',torch.sin(position*frequency)[None,:,None,:])

    def forward(self, video, query_points=None, reference=None, reference_point=None):
        if self.mode in ('final_frame','current_frame'):
            # Enforce access here as well as in the assembler.
            tokens=self.encoder(video[:,:,-1:])[:,0]
        else:
            frames=self.encoder(video)
            if self.mode=='bag': tokens=frames.mean(1)  # commutative before any temporal attention
            else: tokens=(frames+self.time_position[:,:frames.shape[1]]).flatten(1,2)
        ref_tokens=None
        if self.task=='tracking':
            if reference is None: raise ValueError('missing reference RGB')
            ref_tokens=self.encoder(reference[:,:,:1])[:,0]
        return self.head(tokens,query_points,ref_tokens,reference_point)


class FrozenFrameReadout(DiagnosticModel):
    """Image-only reference: framewise frozen features with the common ordered head."""
    def __init__(self, frame_encoder, task, **kwargs):
        super().__init__(frame_encoder,task,'sequence',**kwargs)
        self.encoder.requires_grad_(False).eval()

    def train(self, mode=True):
        super().train(mode);self.encoder.eval();return self
