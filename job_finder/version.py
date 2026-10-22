"""The app's version. The one place it is written: the installer, the release
and the "a new version is available" check all read it from here.

To release a new version: raise it here (1.2.3: the last number for fixes,
the middle one for new features, the first for big changes), commit, then
push a tag with the same number: git tag v1.2.3, git push origin v1.2.3.
"""

VERSION = "0.1.0"
