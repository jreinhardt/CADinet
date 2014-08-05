var camera, controls, scene, renderer;
function attach_renderer(target) {

	var SCREEN_WIDTH = 600, SCREEN_HEIGHT = 400;
	var VIEW_ANGLE = 35, ASPECT = SCREEN_WIDTH / SCREEN_HEIGHT, NEAR = 0.1, FAR = 20000;

	renderer = new THREE.WebGLRenderer();
	renderer.setSize( SCREEN_WIDTH, SCREEN_HEIGHT );
	target.appendChild( renderer.domElement );

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

	//vertex data
	var geom = new THREE.Geometry();
	{% for v in vertices %}
	geom.vertices.push(new THREE.Vector3({{ v[0] }},{{ v[1] }},{{ v[2] }}));
	{%- endfor %}
	{% for f in facets %}
	geom.faces.push(new THREE.Face3({{ f[0] }},{{ f[1] }},{{ f[2] }}));
	{%- endfor %}

	var basematerial = new THREE.MeshBasicMaterial( { color: 0x888888 } );
	var mesh = new THREE.Mesh( geom, basematerial );
	scene.add( mesh );

	var light = new THREE.PointLight( 0xFFFF00 );
	light.position.set( -10000, -10000, 10000 );
	scene.add( light );
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

