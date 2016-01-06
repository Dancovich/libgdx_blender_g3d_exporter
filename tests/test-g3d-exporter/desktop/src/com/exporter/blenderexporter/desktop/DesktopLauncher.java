package com.exporter.blenderexporter.desktop;

import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application;
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration;
import com.exporter.blenderexporter.ExportedModelLoader;

public class DesktopLauncher {
	public static void main (String[] arg) {
        Lwjgl3ApplicationConfiguration config = new Lwjgl3ApplicationConfiguration();

        config.useVsync(true);
        config.setWindowedMode(800, 600);
		config.setTitle("Blender G3D Exporter Test");

        new Lwjgl3Application(new ExportedModelLoader(), config);
	}
}
