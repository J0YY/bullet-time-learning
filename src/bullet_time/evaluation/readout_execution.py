"""Verify actual trusted readout jobs against their fixed artifact contracts.

Run on the execution host/source snapshot. This verifies declared boundaries and
execution, not a complete inventory of private copies, pool admission or release.
"""

from dataclasses import asdict
from pathlib import Path
import sys
import zipfile

from bullet_time.provenance import digest, fields, inside, integer, strict_json
from bullet_time.training.runner import code_files
from .assessment_contract import verify_predictor, verifier_binding
from .job_evidence import file_hash, verify_bound
from .training import ReadoutConfig

FIT_OUTPUTS = {"fit.json", "readout.pt", "readout.pt.json"}
PREDICT_OUTPUTS = {"run.json", "coverage.json", "predictions.csv"}


def _command(command, cwd):
    repo = Path(__file__).resolve().parents[3]
    if Path(cwd).resolve(strict=True) != repo:
        raise ValueError("readout job must use this repository snapshot as cwd")
    if len(command) < 4 or command[:3] != [sys.executable, "-m", "bullet_time.cli"]:
        raise ValueError("fixed readout Python module command required")
    args = list(command[3:])
    threads = 1
    if args[0] == "--threads":
        if len(args) < 3:
            raise ValueError("threads requires a count and readout operation")
        threads = int(args[1])
        integer(threads, "threads", 1)
        args = args[2:]
    if not args or args[0] not in ("fit-readout", "predict-readout"):
        raise ValueError("unsupported readout operation")
    operation, tokens = args[0], args[1:]
    required = {"images", "inputs", "output"}
    if operation == "fit-readout":
        required |= {"labels", "backbone", "readout-config", "groups"}
        optional = {"partitions", "external-cache"}
    else:
        required |= {"checkpoint", "expected", "split"}
        optional = {"device", "external-cache"}
    options = {}
    if len(tokens) % 2:
        raise ValueError("readout options require explicit key/value pairs")
    for key, value in zip(tokens[::2], tokens[1::2], strict=True):
        name = key.removeprefix("--")
        if key != "--" + name or name not in required | optional or name in options:
            raise ValueError("unknown, abbreviated or repeated readout option")
        options[name] = value
    if not required <= options.keys():
        raise ValueError("required readout option missing")
    for key, value in options.items():
        if key not in ("device", "split"):
            path = Path(value)
            if not path.is_absolute() or path != path.resolve():
                raise ValueError("readout paths must be canonical and absolute")
    if operation == "predict-readout" and options["split"] not in ("dev", "assessment"):
        raise ValueError("unsupported prediction split")
    return operation, options, threads


def readout_job_inputs(command, cwd):
    """Collect required actual files for run_bound before launch; no model/data fit.

    All RGB catalog members and exact consumer sources are required. This does
    not execute the CLI, decode pixels, extract source archives or open outcomes.
    Training labels are hashed as files; private assessment labels are never needed.
    """
    _, options, _ = _command(command, cwd)
    source = Path(__file__).resolve().parents[1]
    repo = source.parents[1]
    paths = {source / name for name in code_files()}
    paths.update({repo / "pyproject.toml", repo / "requirements-lock.txt"})
    environment = Path(sys.prefix) / "pyvenv.cfg"
    if environment.is_file():
        paths.add(environment)
    for key, value in options.items():
        if key not in ("device", "split", "output", "external-cache"):
            paths.add(Path(value))
            if key in ("backbone", "checkpoint"):
                paths.add(Path(value + ".json"))
    manifest = Path(options["images"])
    from .inputs import ImageStore

    store = ImageStore(manifest)
    paths.update(inside(store.root, row["rgb_path"]) for row in store.images.values())
    if "external-cache" in options:
        from bullet_time.models.external import lock

        cache, pin = Path(options["external-cache"]), lock()
        archive = cache / "source.zip"
        if file_hash(archive) != pin["archive_sha256"]:
            raise ValueError("external source archive differs from pin")
        paths.add(archive)
        root = cache / ("dinov2-" + pin["revision"])
        # The actual consumer can create missing extracted files; evidence-bound
        # jobs require those files to be prepared and pinned before execution.
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.is_dir():
                    continue
                path = inside(cache, member.filename)
                if not path.is_relative_to(root) or file_hash(path) != digest(bundle.read(member)):
                    raise ValueError("external extracted source differs from archive")
                paths.add(path)
    return {str(path.resolve(strict=True)): file_hash(path) for path in sorted(paths)}


def _job(record, operation, required_roots):
    fields(record, {"path", "request_sha256", "evidence_sha256"})
    directory = Path(record["path"])
    evidence = verify_bound(
        directory,
        expected_request_sha256=record["request_sha256"],
        expected_evidence_sha256=record["evidence_sha256"],
    )
    request = strict_json((directory / "request.json").read_bytes())
    actual, options, threads = _command(request["command"], request["cwd"])
    if actual != operation:
        raise ValueError("evidence is for a different readout operation")
    if options["output"] != request["artifact_output"]:
        raise ValueError("command output differs from the recorded artifact directory")
    outputs = FIT_OUTPUTS if operation == "fit-readout" else PREDICT_OUTPUTS
    if set(evidence["outputs"]) != outputs:
        raise ValueError("readout job output inventory differs")
    for path, checksum in readout_job_inputs(request["command"], request["cwd"]).items():
        if request["inputs"].get(path) != checksum:
            raise ValueError("required readout input/source was not pinned by the job")
    for root in required_roots:
        if not any(root.is_relative_to(Path(denied)) for denied in request["denied_roots"]):
            raise ValueError("required private root was not denied by the job")
    return request, evidence, options, threads


def _runtime(metadata, threads, device):
    from bullet_time.models.runtime import runtime_provenance

    current = runtime_provenance(device)
    current.update(threads=threads, deterministic_algorithms=True)
    if metadata != current:
        raise ValueError("recorded readout runtime differs from command/current host/source")


def verify_readout_execution(
    fit_job,
    prediction_job,
    *,
    expected_path,
    design,
    recipe_sha256,
    private_roots,
    assessment_roots,
    split="assessment",
):
    """Connect two pinned job receipts to the actual fitted predictor and export.

    Caller-supplied roots must come from the full admitted artifact/version registry,
    including reconstruction copies and prior scores. Fitting denies both the full
    assessment sets and private roots; inference denies every private root. This
    verifies that supplied boundary, not its completeness. No release is granted.
    """
    if split not in ("dev", "assessment"):
        raise ValueError("unsupported readout verification split")
    execution = verifier_binding()
    implementation = file_hash(__file__)
    roots = []
    for supplied in (private_roots, assessment_roots):
        group = [Path(p).resolve(strict=True) for p in supplied]
        if not group or any(not p.is_dir() for p in group) or len(set(group)) != len(group):
            raise ValueError("nonempty distinct existing boundary directories required")
        roots.append(group)
    private, assessment = roots
    fit_request, fit_evidence, fit_options, fit_threads = _job(
        fit_job, "fit-readout", private + assessment
    )
    pred_request, pred_evidence, pred_options, pred_threads = _job(
        prediction_job, "predict-readout", private
    )
    fitted = Path(fit_options["output"])
    fit_path = fitted / "fit.json"
    fit = strict_json(fit_path.read_bytes())
    predictions = Path(pred_options["output"])
    meta = strict_json((predictions / "run.json").read_bytes())
    expected = Path(expected_path).resolve(strict=True)
    if pred_options["expected"] != str(expected) or pred_options["split"] != split:
        raise ValueError("prediction job does not use the required expected inventory/split")
    if pred_options["checkpoint"] != str(fitted / "readout.pt"):
        raise ValueError("inference did not consume this job's fitted checkpoint")
    if split == "assessment" and any(
        not any(Path(pred_options[key]).is_relative_to(root) for root in assessment)
        for key in ("images", "inputs")
    ):
        raise ValueError("assessment inference inputs must belong to a declared assessment root")
    supplied_config = ReadoutConfig(**strict_json(Path(fit_options["readout-config"]).read_bytes()))
    supplied_config.validate()
    if asdict(supplied_config) != fit["config"]:
        raise ValueError("fit command config differs from the recorded recipe")
    for key, option in (
        ("input_sha256", "inputs"),
        ("image_manifest_sha256", "images"),
        ("label_sha256", "labels"),
    ):
        if fit[key] != fit_request["inputs"][fit_options[option]]:
            raise ValueError("fit data identity differs from executed command")
    for key, option in (("input_sha256", "inputs"), ("image_manifest_sha256", "images")):
        if meta[key] != pred_request["inputs"][pred_options[option]]:
            raise ValueError("inference data identity differs from executed command")
    if (
        fit["backbone_source"]["checkpoint_sha256"]
        != fit_request["inputs"][fit_options["backbone"]]
    ):
        raise ValueError("fit backbone differs from executed command")
    if meta["readout_sha256"] != fit_evidence["outputs"]["readout.pt"]:
        raise ValueError("export does not bind the actual fitted checkpoint bytes")
    if fit["config"]["task"] != "ssv2":
        if fit["selection"]["group_sha256"] != fit_request["inputs"][fit_options["groups"]]:
            raise ValueError("fitted group selection differs from executed command")
    else:
        if "partitions" not in fit_options:
            raise ValueError("SSv2 fitting requires its actual fixed partition file")
        from .external import validate_external_groups

        audit = validate_external_groups(
            strict_json(Path(fit_options["partitions"]).read_bytes()),
            strict_json(Path(fit_options["groups"]).read_bytes()),
        )
        if audit != fit["consumer_admission"]["external_groups"]:
            raise ValueError("SSv2 admitted partitions/groups differ from executed command")
    _runtime(fit["execution"], fit_threads, fit["config"]["device"])
    _runtime(meta["inference_execution"], pred_threads, pred_options.get("device", "cpu"))
    contract = verify_predictor(fit_path, predictions, expected, design, recipe_sha256, split=split)
    # Recheck the declared bytes/receipts after parsing and contract validation.
    for record in (fit_job, prediction_job):
        verify_bound(
            record["path"],
            expected_request_sha256=record["request_sha256"],
            expected_evidence_sha256=record["evidence_sha256"],
        )
    if verifier_binding() != execution or file_hash(__file__) != implementation:
        raise ValueError("readout execution verifier changed")
    return {
        "schema_version": "bullet-time.readout-execution-binding.v1",
        "contract": contract,
        "fit_job": dict(fit_job),
        "prediction_job": dict(prediction_job),
        "verifier_sha256": implementation,
        "supplied_private_roots": [str(p) for p in private],
        "supplied_assessment_roots": [str(p) for p in assessment],
        "scope": "actual trusted fit/inference jobs and supplied boundaries; not complete registry/data/release admission",
        "complete": contract["complete"],
        "assessment_authorized": False,
        "scientific_gate_pass": False,
    }
