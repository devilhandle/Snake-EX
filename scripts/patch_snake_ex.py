from pathlib import Path

gradle = Path('eka2l1/src/emu/android/app/build.gradle')
strings = Path('eka2l1/src/emu/android/app/src/main/res/values/strings.xml')
java_root = Path('eka2l1/src/emu/android/app/src/main/java/com/github/eka2l1')
main_activity = java_root / 'MainActivity.java'
emulator_java = java_root / 'emu' / 'Emulator.java'

if gradle.exists():
    text = gradle.read_text()
    text = text.replace('applicationId "com.github.eka2l1"', 'applicationId "com.devilhandle.snakeex"')
    gradle.write_text(text)

if strings.exists():
    text = strings.read_text()
    text = text.replace('<string name="app_name" translatable="false">EKA2L1</string>', '<string name="app_name" translatable="false">Snake EX</string>')
    strings.write_text(text)

if not java_root.exists():
    raise SystemExit(f'Missing EKA2L1 Java source root: {java_root}')

# Avoid getAppsList(): it asks native code for icons for every installed app. On a
# fresh bundled installation that path can crash before the game activity opens.
# Raw UID/name enumeration is sufficient to locate Snake EX.
if emulator_java.exists():
    text = emulator_java.read_text()
    if 'public static String[] getInstalledAppsRaw()' not in text:
        marker = '    private static void checkInit() {'
        method = '''    public static String[] getInstalledAppsRaw() {\n        checkInit();\n        return getApps();\n    }\n\n'''
        if marker not in text:
            raise SystemExit('Could not locate Emulator.checkInit()')
        text = text.replace(marker, method + marker, 1)
        emulator_java.write_text(text)

launcher = r'''package com.github.eka2l1;

import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.github.eka2l1.emu.Constants;
import com.github.eka2l1.emu.Emulator;
import com.github.eka2l1.emu.EmulatorActivity;
import io.reactivex.android.schedulers.AndroidSchedulers;
import io.reactivex.schedulers.Schedulers;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

public class MainActivity extends AppCompatActivity {
    private static final String ROM_ASSET = "snakeex/nokia6600.rom";
    private static final String SIS_ASSET = "snakeex/Snake EX-2.sis";
    private static final String DEVICE_CODE = "101FB3DD";
    private static final String MARKER = "snakeex-installed";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            // This performs the same path/folder/native bootstrap as EKA2L1's own
            // shortcut launcher, but does not display the normal app list.
            Emulator.initializeForShortcutLaunch(this);
            bootstrapAndLaunch();
        } catch (Throwable t) {
            showError("EKA2L1 başlatılamadı: " + t.getClass().getSimpleName() + "\n" + String.valueOf(t.getMessage()));
        }
    }

    private void bootstrapAndLaunch() {
        final File marker = new File(Emulator.getEmulatorDir(), MARKER);
        final File rom = new File(getCacheDir(), "snakeex/nokia6600.rom");
        final File sis = new File(getCacheDir(), "snakeex/Snake EX-2.sis");
        copyAssetIfNeeded(ROM_ASSET, rom);
        copyAssetIfNeeded(SIS_ASSET, sis);

        // Always select the Nokia 6600 device before touching the application list.
        // The bundled ROM does not use RPKG, hence an empty RPKG path is intentional.
        installOrSelectDevice(rom)
                .andThen(installIfNeeded(marker, sis))
                .subscribeOn(Schedulers.io())
                .observeOn(AndroidSchedulers.mainThread())
                .subscribe(this::launchInstalledGame, t -> {
                    // If the device already existed, installation can report error 5.
                    // In that case selecting it and looking for the game is still valid.
                    try {
                        selectNokia6600();
                        launchInstalledGame();
                    } catch (Throwable ignored) {
                        showError("Snake EX kurulamadı: " + t.getMessage());
                    }
                });
    }

    private io.reactivex.Completable installOrSelectDevice(File rom) {
        return io.reactivex.Completable.create(emitter -> {
            int result = Emulator.installDevice("", rom.getAbsolutePath(), false);
            if (result == Emulator.INSTALL_DEVICE_ERROR_NONE || result == Emulator.INSTALL_DEVICE_ERROR_ALREADY_EXIST) {
                selectNokia6600();
                emitter.onComplete();
            } else {
                emitter.onError(new java.io.IOException("ROM kurulumu hata kodu: " + result));
            }
        });
    }

    private io.reactivex.Completable installIfNeeded(File marker, File sis) {
        return io.reactivex.Completable.create(emitter -> {
            if (marker.exists()) {
                emitter.onComplete();
                return;
            }
            int result = Emulator.installApp(sis.getAbsolutePath());
            if (result == 0) {
                try { marker.createNewFile(); } catch (Exception ignored) { }
                emitter.onComplete();
            } else {
                // The game may already be installed even when the marker was lost.
                emitter.onError(new java.io.IOException("SIS kurulumu hata kodu: " + result));
            }
        });
    }

    private void selectNokia6600() {
        String[] codes = Emulator.getDeviceFirmwareCodes();
        for (int i = 0; i < codes.length; i++) {
            if (DEVICE_CODE.equalsIgnoreCase(codes[i])) {
                Emulator.setCurrentDevice(i, true);
                return;
            }
        }
        throw new IllegalStateException("Nokia 6600 cihazı bulunamadı");
    }

    private void launchInstalledGame() {
        try {
            selectNokia6600();
            String[] apps = Emulator.getInstalledAppsRaw();
            for (int i = 0; i + 1 < apps.length; i += 2) {
                long uid = Long.parseLong(apps[i]);
                String name = apps[i + 1];
                if (name != null && name.toLowerCase().contains("snake ex")) {
                    Intent intent = new Intent(this, EmulatorActivity.class);
                    intent.setAction(Constants.ACTION_LAUNCH_GAME);
                    intent.putExtra(Constants.KEY_APP_UID, uid);
                    intent.putExtra(Constants.KEY_APP_NAME, name);
                    intent.putExtra(Constants.KEY_DEVICE_CODE, DEVICE_CODE);
                    startActivity(intent);
                    finish();
                    return;
                }
            }
            showError("Snake EX kurulmuş görünmüyor.");
        } catch (Throwable t) {
            showError("Snake EX başlatılamadı: " + t.getClass().getSimpleName() + "\n" + String.valueOf(t.getMessage()));
        }
    }

    private void copyAssetIfNeeded(String asset, File out) {
        if (out.exists() && out.length() > 0) return;
        File parent = out.getParentFile();
        if (parent != null) parent.mkdirs();
        try (InputStream in = getAssets().open(asset); FileOutputStream fos = new FileOutputStream(out)) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) != -1) fos.write(buf, 0, n);
        } catch (Exception e) {
            throw new RuntimeException("Asset kopyalanamadı: " + asset, e);
        }
    }

    private void showError(String message) {
        new AlertDialog.Builder(this)
                .setTitle("Snake EX")
                .setMessage(message)
                .setPositiveButton(android.R.string.ok, (d, w) -> finish())
                .setCancelable(false)
                .show();
    }
}
'''
main_activity.write_text(launcher)
print('Snake EX patch: select Nokia 6600 before SIS/app access and enumerate raw apps without icon loading.')