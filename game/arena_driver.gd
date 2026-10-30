extends SceneTree
## Simulate once, then replay only visual meshes in a separate process.

var request: Dictionary
var output: String
var bodies: Dictionary = {}
var visuals: Dictionary = {}
var materials: Dictionary = {}
var contacts: Array = []
var origin_tick: int = 0
var viewport: SubViewport
var camera: Camera3D

func fail(message: String) -> void:
	printerr(message)
	quit(1)

func _initialize() -> void:
	call_deferred("run")

func read_json(path: String) -> Dictionary:
	var parser := JSON.new()
	var error := parser.parse(FileAccess.get_file_as_string(path))
	if error != OK or not parser.data is Dictionary:
		fail("Invalid JSON: " + path)
		return {}
	return parser.data

func write_json(path: String, data: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("Cannot write " + path)
		return
	file.store_string(JSON.stringify(data, "\t", true, true) + "\n")

func vec(values: Array) -> Vector3:
	return Vector3(values[0], values[1], values[2])

func arr(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func transform_record(value: Transform3D) -> Array:
	return [arr(value.basis.x), arr(value.basis.y), arr(value.basis.z), arr(value.origin)]

func decode_transform(value: Array) -> Transform3D:
	return Transform3D(Basis(vec(value[0]), vec(value[1]), vec(value[2])), vec(value[3]))

func mesh_for(spec: Dictionary) -> Mesh:
	if spec.kind == "sphere":
		var sphere := SphereMesh.new()
		sphere.radius = spec.radius
		sphere.height = 2.0 * spec.radius
		sphere.radial_segments = 24
		sphere.rings = 12
		return sphere
	var box := BoxMesh.new()
	box.size = vec(spec.size)
	return box

func shape_for(spec: Dictionary) -> Shape3D:
	if spec.kind == "sphere":
		var sphere := SphereShape3D.new()
		sphere.radius = spec.radius
		return sphere
	var box := BoxShape3D.new()
	box.size = vec(spec.size)
	return box

func material_for(spec: Dictionary, mask: bool = false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	if mask:
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.albedo_color = Color.BLACK
		if spec.role == "projectile":
			material.albedo_color = Color.RED
		elif spec.role == "target":
			material.albedo_color = Color.GREEN
	else:
		material.albedo_color = Color(spec.color[0], spec.color[1], spec.color[2])
		material.roughness = 0.85
		if spec.role == "floor":
			var texture := Image.create(64, 64, false, Image.FORMAT_RGB8)
			for y in range(64):
				for x in range(64):
					var shade := 1.0 if (x / 8 + y / 8) % 2 == 0 else 0.8
					texture.set_pixel(x, y, Color(shade, shade, shade))
			material.albedo_texture = ImageTexture.create_from_image(texture)
	return material

func on_contact(other: Node, body_id: String) -> void:
	contacts.append({"physics_tick": Engine.get_physics_frames() - origin_tick,
		"a": body_id, "b": str(other.name)})

func simulate() -> void:
	var world := Node3D.new()
	root.add_child(world)
	for spec in request.objects:
		var body: PhysicsBody3D
		if spec.rigid:
			var rigid := RigidBody3D.new()
			rigid.mass = spec.mass
			rigid.freeze = true
			rigid.can_sleep = false
			rigid.continuous_cd = true
			rigid.contact_monitor = true
			rigid.max_contacts_reported = 8
			rigid.linear_damp = 0.05
			rigid.angular_damp = 0.1
			var physics_material := PhysicsMaterial.new()
			physics_material.friction = spec.friction
			physics_material.bounce = spec.bounce
			rigid.physics_material_override = physics_material
			rigid.body_entered.connect(on_contact.bind(spec.id))
			body = rigid
		else:
			body = StaticBody3D.new()
		body.name = spec.id
		body.position = vec(spec.position)
		var shape := CollisionShape3D.new()
		shape.shape = shape_for(spec)
		body.add_child(shape)
		world.add_child(body)
		bodies[spec.id] = body
	# Let the physics server register the initially frozen bodies.
	await physics_frame
	await physics_frame
	await process_frame
	origin_tick = Engine.get_physics_frames()
	for spec in request.objects:
		if spec.rigid and spec.role != "projectile":
			bodies[spec.id].freeze = false
	var states: Array = []
	var total_steps: int = request.start_tick + 15 * request.stride_ticks
	for tick in range(total_steps + 1):
		if tick > 0:
			await physics_frame
			await process_frame
		if Engine.get_physics_frames() - origin_tick != tick:
			fail("Physics clock skipped a fixed step")
			return
		if tick == request.launch_tick:
			var projectile: RigidBody3D = bodies["projectile"]
			projectile.freeze = false
			projectile.linear_velocity = vec(request.launch_velocity)
		if tick >= request.start_tick and (tick - int(request.start_tick)) % int(request.stride_ticks) == 0:
			var objects: Dictionary = {}
			for spec in request.objects:
				var body: PhysicsBody3D = bodies[spec.id]
				var record := {"transform": transform_record(body.global_transform)}
				if spec.rigid:
					record["linear_velocity"] = arr(body.linear_velocity)
					record["angular_velocity"] = arr(body.angular_velocity)
					record["frozen"] = body.freeze
				objects[spec.id] = record
			states.append({"physics_tick": tick, "seconds": tick / 64.0, "objects": objects})
	if states.size() != 16:
		fail("Wrong state count")
		return
	write_json(output, {"schema_version": "bullet-time.arena-state.v1", "request": request,
		"engine_version": Engine.get_version_info(), "physics_hz": 64, "states": states,
		"contacts": contacts, "capture": "Godot fixed-step rigid-body simulation; meshes replayed separately"})
	print("SIMULATED ", request.grid_id, " states=", states.size())
	quit()

func visual_state() -> Dictionary:
	var state: Dictionary = {}
	for id in visuals:
		state[id] = transform_record(visuals[id].global_transform)
	return state

func capture() -> Image:
	viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	image.convert(Image.FORMAT_RGB8)
	return image

func set_masks(enabled: bool) -> void:
	for spec in request.objects:
		visuals[spec.id].material_override = material_for(spec, true) if enabled else materials[spec.id]

func render(saved: Dictionary) -> void:
	if DisplayServer.get_name() == "headless":
		fail("Headless display has no real renderer; use a native display for RGB capture")
		return
	viewport = SubViewport.new()
	viewport.size = Vector2i(224, 224)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color(0.12, 0.15, 0.19)
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color.WHITE
	environment.environment.ambient_light_energy = 0.6
	world.add_child(environment)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55, -25, 0)
	light.light_energy = 1.1
	light.shadow_enabled = true
	world.add_child(light)
	for spec in request.objects:
		var mesh := MeshInstance3D.new()
		mesh.mesh = mesh_for(spec)
		mesh.name = spec.id
		materials[spec.id] = material_for(spec)
		mesh.material_override = materials[spec.id]
		world.add_child(mesh)
		visuals[spec.id] = mesh
	camera = Camera3D.new()
	camera.fov = request.camera.fov_degrees
	camera.near = 0.05
	camera.far = 60.0
	world.add_child(camera)
	camera.make_current()
	var records: Array = []
	var observed_cameras: Array = []
	var state_snapshots: Array = []
	for t in range(16):
		for id in visuals:
			visuals[id].global_transform = decode_transform(saved.states[t].objects[id].transform)
		var expected := visual_state()
		var state_json := JSON.stringify(expected, "", true, true)
		state_snapshots.append(state_json)
		for c in range(16):
			camera.position = vec(request.camera.poses[c])
			camera.look_at(vec(request.camera.look_at), Vector3.UP)
			if t == 0:
				observed_cameras.append(transform_record(camera.global_transform))
			var image: Image = await capture()
			var relative := "t%02d-c%02d.png" % [t, c]
			if image.save_png(output.path_join("rgb").path_join(relative)) != OK:
				fail("RGB write failed")
				return
			set_masks(true)
			var mask: Image = await capture()
			if mask.save_png(output.path_join("masks").path_join(relative)) != OK:
				fail("Mask write failed")
				return
			set_masks(false)
			if visual_state() != expected:
				fail("Camera/render pass changed visual state")
				return
			records.append({"world_time_index": t, "camera_index": c,
				"rgb_file": relative, "frozen_state_unchanged": true,
				"before_state_sha256": state_json.sha256_text(),
				"after_state_sha256": JSON.stringify(visual_state(), "", true, true).sha256_text()})
	# Revisit saved states/cameras in a different order. Never replace corpus images.
	var repeats: Array = []
	for indices in [[15, 15], [0, 0], [8, 7], [0, 15]]:
		var t: int = indices[0]
		var c: int = indices[1]
		for id in visuals:
			visuals[id].global_transform = decode_transform(saved.states[t].objects[id].transform)
		camera.position = vec(request.camera.poses[c])
		camera.look_at(vec(request.camera.look_at), Vector3.UP)
		var repeated: Image = await capture()
		var original := Image.load_from_file(output.path_join("rgb/t%02d-c%02d.png" % [t, c]))
		original.convert(Image.FORMAT_RGB8)
		if repeated.save_png(output.path_join("repeat/t%02d-c%02d.png" % [t, c])) != OK:
			fail("Repeat write failed")
			return
		var equal: bool = original.get_data() == repeated.get_data()
		repeats.append({"world_time_index": t, "camera_index": c, "pixel_identical": equal})
		if not equal:
			fail("Repeat render changed pixels")
			return
	write_json(output.path_join("render.json"), {"schema_version": "bullet-time.arena-render.v1",
		"engine_version": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method(),
		"video_adapter": RenderingServer.get_video_adapter_name(), "display": DisplayServer.get_name(),
		"cells": records, "camera_transforms": observed_cameras, "repeat_checks": repeats,
		"replayed_state_json": state_snapshots,
		"physics_nodes_in_replay": 0, "temporal_effects": false})
	print("RENDERED ", request.grid_id, " cells=", records.size())
	quit()

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 3:
		fail("Expected MODE INPUT_JSON OUTPUT_PATH")
		return
	output = args[2]
	if args[0] == "simulate":
		request = read_json(args[1])
		await simulate()
	elif args[0] == "render":
		var saved := read_json(args[1])
		request = saved.request
		await render(saved)
	else:
		fail("Unknown capture mode")
