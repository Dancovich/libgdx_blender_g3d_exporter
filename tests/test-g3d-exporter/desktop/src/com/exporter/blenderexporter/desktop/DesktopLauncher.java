package com.exporter.blenderexporter.desktop;

import com.badlogic.gdx.backends.lwjgl.LwjglApplication;
import com.badlogic.gdx.backends.lwjgl.LwjglApplicationConfiguration;
import com.exporter.blenderexporter.ExportedModelLoader;

public class DesktopLauncher {
	public static void main (String[] arg) {
		LwjglApplicationConfiguration config = new LwjglApplicationConfiguration();

		config.width = 800;
        config.height = 600;
        config.title = "Blender G3D Exporter Test";

		new LwjglApplication(new ExportedModelLoader(), config);
	}
}
