package com.exporter.blenderexporter;

import com.badlogic.gdx.Application;
import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.InputMultiplexer;
import com.badlogic.gdx.assets.AssetManager;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.PerspectiveCamera;
import com.badlogic.gdx.graphics.g3d.Environment;
import com.badlogic.gdx.graphics.g3d.Model;
import com.badlogic.gdx.graphics.g3d.ModelBatch;
import com.badlogic.gdx.graphics.g3d.ModelInstance;
import com.badlogic.gdx.graphics.g3d.attributes.ColorAttribute;
import com.badlogic.gdx.graphics.g3d.environment.DirectionalLight;
import com.badlogic.gdx.graphics.g3d.utils.AnimationController;
import com.badlogic.gdx.graphics.g3d.utils.CameraInputController;
import com.badlogic.gdx.math.Vector3;

public class ExportedModelLoader extends ApplicationAdapter {

    // G3DJ Model
    public static final String SOLDIER_MODEL_PATH = "data/soldier.g3dj";
    public static final String BOX_MODEL_PATH = "data/box.g3dj";

    // G3DB Model
    //public static final String SOLDIER_MODEL_PATH = "data/soldier.g3db";
    //public static final String BOX_MODEL_PATH = "data/box.g3db";

	public Environment environment;
	public PerspectiveCamera cam;
	public CameraInputController camController;
	public ModelBatch modelBatch;

    public Model soldierModel;
    public Model boxModel;

    public ModelInstance soldierInstance;
    public ModelInstance boxInstance;

    public AssetManager assets;

	public AnimationController animationController;

	@Override
	public void create () {
		Gdx.app.setLogLevel(Application.LOG_DEBUG);

		modelBatch = new ModelBatch();

		// creates some basic lighting
		environment = new Environment();
		environment.set(new ColorAttribute(ColorAttribute.AmbientLight, 0.4f, 0.4f, 0.4f, 1f));
		environment.add(new DirectionalLight().set(0.8f, 0.8f, 0.8f, -1f, -0.8f, -0.2f));

		// Here we load our soldierModel
		assets = new AssetManager();
		assets.load(SOLDIER_MODEL_PATH, Model.class);
        assets.load(BOX_MODEL_PATH, Model.class);
		assets.finishLoading();

		soldierModel = assets.get(SOLDIER_MODEL_PATH);
		soldierInstance = new ModelInstance(soldierModel);

        boxModel = assets.get(BOX_MODEL_PATH);
        boxInstance = new ModelInstance(boxModel);
        boxInstance.transform.translate(new Vector3(5f,0f,0f));

		// Used to run the exported animation
		animationController = new AnimationController(soldierInstance);
		animationController.setAnimation("Run", -1);
	}

	@Override
	public void render () {
		// Update out camera and animation
		camController.update();
		animationController.update(Gdx.graphics.getDeltaTime());

		Gdx.gl.glViewport(0, 0, Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
		Gdx.gl.glClearColor(1, 1, 1, 1);
		Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT | GL20.GL_DEPTH_BUFFER_BIT);

		// Render the soldierModel
		modelBatch.begin(cam);
		modelBatch.render(soldierInstance, environment);
        //modelBatch.render(boxInstance, environment);
		modelBatch.end();
	}

	@Override
	public void dispose () {
		modelBatch.dispose();
        soldierInstance = null;
		soldierModel = null;
        boxInstance = null;
        boxModel = null;
        assets.dispose();
	}

	@Override
	public void resize (int width, int height) {
		float vFoV = 50f * ((float)height/(float)width);

		cam = new PerspectiveCamera(vFoV, width, height);
		cam.position.set(0f, 3f, 10f);
		cam.up.set(Vector3.Y);
		cam.lookAt(0f, 3f, 0f);
		cam.near = 1f;
		cam.far = 300f;
		cam.update();

        if (camController == null) {
            camController = new CameraInputController(cam);

            InputMultiplexer mx = new InputMultiplexer();
            mx.addProcessor(camController);
            Gdx.input.setInputProcessor(mx);
        }
        else {
            camController.camera = cam;
        }
	}

	@Override
	public void pause () {
	}

	@Override
	public void resume () {
	}
}
