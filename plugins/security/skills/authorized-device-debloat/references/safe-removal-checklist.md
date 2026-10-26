# Safe-removal checklist

Per package, on an owned or authorised device.

1. **Evidence recorded** — package name, system or user, installer, receivers, services,
   observed endpoints, and the reason it is classed as ad or bloat.
2. **Not shared or critical** — not the only launcher, input method, CEC/HDMI handler, system
   updater, setup wizard, Play services, or a DRM component.
3. **Backup** — `adb shell pm path <pkg>` and `adb pull` of the APK or APKs; the package
   baseline lists saved.
4. **Least-invasive step first:**

   ```bash
   adb shell pm disable-user --user 0 <pkg>     # reversible
   adb shell pm uninstall -k --user 0 <pkg>     # removes for user 0, keeps the image copy
   ```

5. **Rollback ready:**

   ```bash
   adb shell pm enable <pkg>
   adb shell cmd package install-existing <pkg>
   ```

6. **Acceptance after reboot** — boots to home, remote and CEC work, network, settings,
   updates and licensed streaming apps play.
7. **Logged** — command, time, result, and rollback used or not.
8. **Finish** — network ADB disabled, developer options off if the owner wants, and the
   factory-reset path for this model written down.
