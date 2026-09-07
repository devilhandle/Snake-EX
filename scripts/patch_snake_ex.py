from pathlib import Path

# Build a Snake EX launcher on top of the upstream EKA2L1 Android runtime.
# The ROM and SIS are copied into APK assets by the workflow. On first launch
# MainActivity installs the ROM and SIS through EKA2L1's own Java API, then
# launches the installed Snake EX app directly. No EKA2L1 app-list UI is shown.

gradle = Path('eka2l1/src/emu/android/app/build.gradle')
strings = Path('eka2l1/src/emu/android/app/src/main/res/values/strings.xml')
java_root = Path('eka2l1/src/emu/android/app/src/main/java/com/github/eka2l1')
main_activity = java_root / 'MainActivity.java'

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

# Replace only the launcher Activity. The emulator engine and EmulatorActivity
# remain upstream, so native initialization is not reimplemented here.
launcher = r'''package com.github.eka2l1;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.github.eka2l1.applist.AppItem;
import com.github.eka2l1.emu.Constants;
import com.github.eka2l1.emu.Emulator;
import io.reactivex.android.schedulers.AndroidSchedulers;
import io.reactivex.schedulers.Schedulers;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.ArrayList;

public class MainActivity extends AppCompatActivity {
    private static final String ROM_ASSET = "snakeex/nokia6600.rom";
    private static final String SIS_ASSET = "snakeex/Snake EX-2.sis";
    private static final String DEVICE_CODE = "101FB3DD";
    private static final String MARKER = "snakeex-installed";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        // Do not render the normal EKA2L1 launcher UI.
        Emulator.initializeForShortcutLaunch(this);
        bootstrapAndLaunch();
    }

    private void bootstrapAndLaunch() {
        final File marker = new File(Emulator.getEmulatorDir(), MARKER);
        copyAssetIfNeeded(ROM_ASSET, "snakeex/nokia6600.rom");
        copyAssetIfNeeded(SIS_ASSET, "snakeex/Snake EX-2.sis");
        final File rom = new File(getCacheDir(), "snakeex/nokia6600.rom");
        final File sis = new File(getCacheDir(), "snakeex/Snake EX-2.sis");

        if (marker.exists()) {
            launchInstalledGame();
            return;
        }

        Emulator.subscribeInstallDevice("", rom.getAbsolutePath(), false)
                .subscribeOn(Schedulers.io())
                .andThen(Emulator.subscribeInstallApp(sis.getAbsolutePath()))
                .subscribeOn(Schedulers.io())
                .observeOn(AndroidSchedulers.mainThread())
                .subscribe(() -> {
                    try { marker.createNewFile(); } catch (Exception ignored) { }
                    launchInstalledGame();
                }, throwable -> {
                    // If the device already exists, continue to the app list and
                    // install/launch the SIS without exposing the emulator UI.
                    launchInstalledGame();
                });
    }

    private void launchInstalledGame() {
        Emulator.getAppsList()
                .subscribeOn(Schedulers.io())
                .observeOn(AndroidSchedulers.mainThread())
                .subscribe(items -> {
                    AppItem found = null;
                    for (AppItem item : items) {
                        if (item.getTitle() != null && item.getTitle().toLowerCase().contains("snake ex")) {
                            found = item;
                            break;
                        }
                    }
                    if (found == null) {
                        // Some SIS builds use a different title. Try the UID from
                        // the installed SIS by selecting the first non-system app.
                        for (AppItem item : items) {
                            if (item.getUid() != 0) { found = item; break; }
                        }
                    }
                    if (found == null) {
                        finish();
                        return;
                    }
                    Intent intent = new Intent(this, EmulatorActivity.class);
                    intent.putExtra(Constants.KEY_ACTION, Constants.ACTION_LAUNCH_GAME);
                    intent.putExtra(Constants.KEY_APP_UID, found.getUid());
                    intent.putExtra(Constants.KEY_APP_NAME, found.getTitle());
                    intent.putExtra(Constants.KEY_DEVICE_CODE, DEVICE_CODE);
                    intent.putExtra(Constants.KEY_APP_IS_SHORTCUT, true);
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                    startActivity(intent);
                    finish();
                }, throwable -> finish());
    }

    private void copyAssetIfNeeded(String asset, String name) {
        File out = new File(getCacheDir(), name);
        if (out.exists() && out.length() > 0) return;
        File parent = out.getParentFile();
        if (parent != null) parent.mkdirs();
        try (InputStream in = getAssets().open(asset); FileOutputStream fos = new FileOutputStream(out)) {
            byte[] buf = new byte[1024 * 64];
            int n;
            while ((n = in.read(buf)) != -1) fos.write(buf, 0, n);
        } catch (Exception e) {
            throw new RuntimeException("Failed to copy Snake EX asset: " + asset, e);
        }
    }
}
'''
main_activity.write_text(launcher)
print('Snake EX patch: ROM/SIS assets are installed through EKA2L1 APIs and Snake EX is launched directly.')
