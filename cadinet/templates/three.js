var camera, controls, scene, renderer;
function attach_renderer(target) {
	var SCREEN_WIDTH = 750, SCREEN_HEIGHT = 400;
	var VIEW_ANGLE = 35, ASPECT = SCREEN_WIDTH / SCREEN_HEIGHT, NEAR = 0.1, FAR = 20000;

	scene = new THREE.Scene();

	camera = new THREE.PerspectiveCamera(
		VIEW_ANGLE, // Field of view
		ASPECT, // Aspect ratio
		NEAR, // Near plane
		FAR // Far plane
	);
	camera.position.set({{ cam.x }},{{ cam.y }},{{ cam.z }});
	camera.lookAt(scene.position);

	controls = new THREE.TrackballControls( camera );
	controls.rotateSpeed = 1.0;
	controls.zoomSpeed = 1.2;
	controls.panSpeed = 0.8;
	controls.noZoom = false;
	controls.noPan = false;
	controls.staticMoving = true;
	controls.dynamicDampingFactor = 0.3;
	controls.keys = [ 65, 83, 68 ];


	var geom = new THREE.Geometry();
	{% for v in vertices %}
	geom.vertices.push(new THREE.Vector3({{ v[0] }},{{ v[1] }},{{ v[2] }}));
	{%- endfor %}
	{% for f in facets %}
	geom.faces.push(new THREE.Face3({{ f[0] }},{{ f[1] }},{{ f[2] }}));
	{%- endfor %}

	geom.computeFaceNormals()

	var basematerial = new THREE.MeshPhongMaterial( { ambient: 0x030303, color: 0x555555, specular: 0x666666, shininess: 10 } );

	var mesh = new THREE.Mesh( geom, basematerial );
	scene.add( mesh );

	var d1 = new THREE.DirectionalLight(0xffffff); d1.position.set(1,1,1).normalize(); scene.add(d1);
	var d2 = new THREE.DirectionalLight(0xffffff); d2.position.set(-1,-1,-1).normalize(); scene.add(d2);

	renderer = new THREE.WebGLRenderer({ antialias : true });
	renderer.setSize( SCREEN_WIDTH, SCREEN_HEIGHT );
	renderer.setClearColor(0xffffff, 1)

	target.appendChild( renderer.domElement );

	renderer.render( scene, camera );
	animate();
};

function animate(){
	requestAnimationFrame( animate );
	render();
};

function render(){
	controls.update();
	renderer.render( scene, camera );
};

