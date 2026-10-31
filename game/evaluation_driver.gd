extends "res://arena_driver.gd"
## Independent Godot shape casts and mesh-only development measurement capture.

func setup_measurement_world() -> void:
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
	environment.environment.background_color = Color(0.1, 0.13, 0.17)
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color.WHITE
	environment.environment.ambient_light_energy = 0.7
	world.add_child(environment)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-60, -20, 0)
	light.light_energy = 0.8
	light.shadow_enabled = false
	world.add_child(light)
	for spec in request.objects:
		var mesh := MeshInstance3D.new()
		mesh.mesh = mesh_for(spec)
		mesh.name = spec.id
		mesh.position = vec(spec.position)
		var material := StandardMaterial3D.new()
		material.albedo_color = Color(spec.color[0], spec.color[1], spec.color[2])
		material.roughness = 0.9
		mesh.material_override = material
		materials[spec.id] = material
		world.add_child(mesh)
		visuals[spec.id] = mesh
		if spec.id == "target":
			var body := StaticBody3D.new()
			body.collision_layer = 2
			body.collision_mask = 0
			body.position = vec(spec.position)
			var shape := CollisionShape3D.new()
			shape.shape = shape_for(spec)
			body.add_child(shape)
			world.add_child(body)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = request.camera.size
	camera.near = 0.05
	camera.far = 60
	world.add_child(camera)
	camera.position = vec(request.camera.position)
	camera.look_at(vec(request.camera.look_at), vec(request.camera.up))
	camera.make_current()

func measurement_masks(enabled: bool, isolated: bool = false) -> void:
	for id in visuals:
		visuals[id].visible = not isolated or id == "projectile"
		if enabled:
			var material := StandardMaterial3D.new()
			material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			material.albedo_color = Color.RED if id == "projectile" else Color.GREEN if id == "target" else Color.BLUE if id == "distractor" else Color.BLACK
			visuals[id].material_override = material
		else:
			visuals[id].material_override = materials[id]

func camera_point(position: Vector3) -> Array:
	# Godot coordinates refer to viewport edges; dataset coordinates denote centers.
	var p := camera.unproject_position(position) - Vector2(0.5, 0.5)
	return [p.x / 223.0, p.y / 223.0]

func contact_probes() -> Array:
	await physics_frame
	await physics_frame
	var space := viewport.find_world_3d().direct_space_state
	var reports: Array = []
	for probe in request.probes:
		var shape := SphereShape3D.new()
		shape.radius = probe.radius
		var query := PhysicsShapeQueryParameters3D.new()
		query.shape = shape
		query.collision_mask = 2
		query.margin = 0.0001
		var hits: Array = []
		for step in range(probe.positions.size()):
			query.transform = Transform3D(Basis.IDENTITY, vec(probe.positions[step]))
			query.motion = vec(probe.motions[step])
			var fractions := space.cast_motion(query)
			if fractions[0] < 1.0:
				hits.append({"step": step + 1, "safe_fraction": fractions[0], "unsafe_fraction": fractions[1]})
		reports.append({"branch": probe.branch, "hits": hits, "margin": query.margin})
	return reports

func render_measurement() -> void:
	if DisplayServer.get_name() == "headless":
		fail("A native display is required for measurement RGB")
		return
	setup_measurement_world()
	var contact_evidence: Array = await contact_probes()
	var records: Array = []
	for key in request.frames:
		for id in request.frames[key]:
			visuals[id].position = vec(request.frames[key][id])
		var before := JSON.stringify(visual_state(), "", true, true)
		var image: Image = await capture()
		if image.save_png(output.path_join("rgb").path_join(key + ".png")) != OK:
			fail("Cannot save RGB")
			return
		measurement_masks(true)
		var mask: Image = await capture()
		if mask.save_png(output.path_join("masks").path_join(key + ".png")) != OK:
			fail("Cannot save object mask")
			return
		measurement_masks(false)
		var points := {"projectile": camera_point(visuals["projectile"].position)}
		if visuals.has("target"):
			points["target"] = camera_point(visuals["target"].position)
		var annotation: Dictionary = {}
		if request.task == "tracking":
			var surface: Vector3 = visuals["projectile"].position + vec(request.tracking.local_surface_point)
			annotation = {"surface_point": camera_point(surface),
				"facing_camera": vec(request.tracking.normal).dot(camera.position - surface) > 0}
			measurement_masks(true, true)
			var full_mask: Image = await capture()
			if full_mask.save_png(output.path_join("full-masks").path_join(key + ".png")) != OK:
				fail("Cannot save isolated target mask")
				return
			measurement_masks(false)
		records.append({"key": key, "projected_centers": points, "tracking": annotation,
			"visual_state": visual_state(),
			"before_state_sha256": before.sha256_text(),
			"after_state_sha256": JSON.stringify(visual_state(), "", true, true).sha256_text()})
	var repeat_keys: Array = [request.frames.keys()[-1], request.frames.keys()[0]]
	var repeats: Array = []
	for key in repeat_keys:
		for id in request.frames[key]:
			visuals[id].position = vec(request.frames[key][id])
		var repeat: Image = await capture()
		var original := Image.load_from_file(output.path_join("rgb").path_join(key + ".png"))
		original.convert(Image.FORMAT_RGB8)
		var equal: bool = original.get_data() == repeat.get_data()
		if repeat.save_png(output.path_join("repeat").path_join(key + ".png")) != OK:
			fail("Cannot save repeated capture")
			return
		repeats.append({"key": key, "identical": equal})
		if not equal:
			fail("Repeated measurement RGB differs")
			return
	write_json(output.path_join("render.json"), {
		"schema_version": "bullet-time.measurement-render.v1", "request": request,
		"engine_version": Engine.get_version_info(),
		"renderer": RenderingServer.get_current_rendering_method(),
		"video_adapter": RenderingServer.get_video_adapter_name(),
		"display": DisplayServer.get_name(), "temporal_effects": false,
		"records": records, "repeats": repeats, "contact_probes": contact_evidence,
		"camera_transform": transform_record(camera.global_transform)})
	print("MEASUREMENT ", request.group_id, " frames=", records.size())
	quit()

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		fail("Expected INPUT_JSON OUTPUT_DIRECTORY")
		return
	request = read_json(args[0])
	output = args[1]
	await render_measurement()
