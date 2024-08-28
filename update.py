import os
import zipfile
import glob
import hashlib
import json
import datetime
from os.path import basename


def calculate_hash_and_size(filepath):
    """file -> SHA1, size"""
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest().upper(), os.path.getsize(filepath)


print("[UPDATE.PY] Starting update process...")

# 1. Unzip ./tmp/*.zip
print("\n[UPDATE.PY] Unzipping artifacts...")
os.makedirs("./tmp/release/", exist_ok=True)
for file in glob.glob("./tmp/release/*"):
    print(f"Removing {file}...")
    os.remove(file)
zip_files = glob.glob("./tmp/*.zip")
for zip_file in zip_files:
    print(f"Extracting {zip_file}...")
    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall("./tmp/release")
print("./tmp/release/")
for file in glob.glob("./tmp/release/*"):
    if file.endswith("bundle-size.json"):
        os.remove(file)
    print(f"    {basename(file)}")


# 2. Extract version number from x64 .nupkg file
print("\n[UPDATE.PY] Reading version number from x64 .nupkg file...")
x64_nupkg_files = glob.glob("./tmp/release/*x64*.nupkg")
if not x64_nupkg_files:
    raise ValueError("No x64 .nupkg files found.")
x64_nupkg_file = basename(x64_nupkg_files[0])
if "GitHubDesktop-" not in x64_nupkg_file or "-x64-full.nupkg" not in x64_nupkg_file:
    raise ValueError(f'Unsupported filename: "{x64_nupkg_file}"')
version = x64_nupkg_file.replace("GitHubDesktop-", "").replace("-x64-full.nupkg", "")
print(f"Version: {version}")

if "-" not in version:
    version_type = "production"
elif "beta" in version:
    version_type = "beta"
else:
    raise ValueError("Unsupported version type.")
print(f"Type: {version_type}")


# 3. Fix filenames
print("\n[UPDATE.PY] Fixing filenames...")
print("./tmp/release/")
x64_nupkg_file = f"./tmp/release/GitHubDesktop-{version}-x64-full.nupkg"
x64_nupkg_new = f"./tmp/release/GitHubDesktop-{version}-full.nupkg"
os.rename(x64_nupkg_file, x64_nupkg_new)
print(f"    {basename(x64_nupkg_file)} --> {basename(x64_nupkg_new)}")
arm64_nupkg_file = f"./tmp/release/GitHubDesktop-{version}-arm64-full.nupkg"
arm64_nupkg_new = f"./tmp/release/GitHubDesktop-{version}.nupkg"
os.rename(arm64_nupkg_file, arm64_nupkg_new)
print(f"    {basename(arm64_nupkg_file)} --> {basename(arm64_nupkg_new)}")

# -- Windows
for file in glob.glob("./tmp/release/*.exe") + glob.glob("./tmp/release/*.msi"):
    new_file = file.replace("GitHubDesktopSetup", "GitHubDesktop-Windows")
    os.rename(file, new_file)
    print(f"    {basename(file)} --> {basename(new_file)}")

# -- macOS
for zip_file in glob.glob("./tmp/release/*.zip"):
    if "GitHub Desktop" not in zip_file:
        continue
    new_zip_file = zip_file.replace("GitHub Desktop", "GitHubDesktop-macOS")
    os.rename(zip_file, new_zip_file)
    print(f"    {basename(zip_file)} --> {basename(new_zip_file)}")


# 4. Write release body
print("\n[UPDATE.PY] Writing release info...")

RELEASE_INFO = f"""## GitHub Desktop 汉化版
版本：{version}
渠道：{version_type}

由 GitHub Action 自动发布
该汉化版支持自动更新，服务器为 [zetaloop/desktop-metadata](https://github.com/zetaloop/desktop-metadata)"""

print(f"'''\n{RELEASE_INFO}\n'''")
with open("./tmp/release_body.txt", "w", encoding="utf-8") as f:
    print("<Release Info> --> ./tmp/release_body.txt...")
    f.write(RELEASE_INFO)


# 5. Export environment variables for GitHub Actions
print("\n[UPDATE.PY] Exporting environment variables...")
github_env = os.getenv("GITHUB_ENV")
is_prerelease = "true" if version_type == "beta" else "false"
if github_env:
    with open(github_env, "a") as env_file:
        env_file.write(f"DESKTOP_VERSION={version}\n")
        print(f"DESKTOP_VERSION={version}")
        env_file.write(f"IS_PRERELEASE={is_prerelease}\n")
        print(f"IS_PRERELEASE={is_prerelease}")
else:
    print('"GITHUB_ENV" not found. Skipping exporting environment variables.')


# 6. Write metadata files
print("\n[UPDATE.PY] Writing metadata files...")

# -- Windows
for platform in ["x64", "arm64"]:
    x64_nupkg_file = (
        f"./tmp/release/GitHubDesktop-{version}-full.nupkg"
        if platform == "x64"
        else f"./tmp/release/GitHubDesktop-{version}.nupkg"
    )
    hash, size = calculate_hash_and_size(x64_nupkg_file)
    url = f"https://github.com/zetaloop/desktop/releases/download/release-{version}/{os.path.basename(x64_nupkg_file)}"
    release_file = f"./metadata/win32-{platform}-{version_type}/RELEASES"
    release_line = f"{hash} {url} {size}"
    with open(release_file, "w") as f:
        print(f"{release_file}")
        print(f"    {release_line}")
        f.write(release_line)

# -- macOS
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
for platform in ["x64", "arm64"]:
    zip_file = f"./tmp/release/GitHubDesktop-macOS-{platform}.zip"
    url = f"https://github.com/zetaloop/desktop/releases/download/release-{version}/{os.path.basename(zip_file)}"
    metadata = {
        "url": url,
        "name": "",
        "notes": [],
        "pub_date": now,
        "version": version,
    }
    release_file = f"./metadata/darwin-{platform}-{version_type}/releases.json"
    release_line = json.dumps(metadata)
    with open(release_file, "w", encoding="utf-8") as f:
        print(f"{release_file}")
        print(f"    {release_line}")
        f.write(release_line)


# 7. Finish
print("\n[UPDATE.PY] All tasks completed successfully :)")
