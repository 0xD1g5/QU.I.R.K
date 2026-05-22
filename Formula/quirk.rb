# Homebrew Formula for QU.I.R.K. (Quantum Infrastructure Readiness Kit)
#
# This file is the CANONICAL source for the formula. On each release the file
# is copied verbatim into the tap repo `0xD1g5/homebrew-quirk` at path
# `Formula/quirk.rb`, which is what `brew install 0xD1g5/quirk/quirk` resolves.
#
# RELEASE-TIME UPDATES (see docs/release-process.md, "Homebrew Tap" section):
# the `url`, `sha256`, and the implicit version (encoded in the `url`
# filename) MUST be bumped on every PyPI release. The placeholders below are
# intentional and point at version 0.0.0 / a zero-hash so the formula is
# unbuildable until a real release lands.
#
# The formula installs from PyPI (distribution name `quirk-scanner`, NOT `quirk`)
# into a virtualenv under `libexec`, then symlinks the `quirk` binary into
# `bin`. This is the Homebrew-idiomatic equivalent of a pipx-managed venv
# (per LAUNCH-02 success criterion): one isolated Python environment per CLI,
# zero pollution of the system / Homebrew Python site-packages.
class Quirk < Formula
  include Language::Python::Virtualenv

  desc "Quantum Infrastructure Readiness Kit -- crypto inventory + quantum-readiness scanner"
  homepage "https://github.com/0xD1g5/QU.I.R.K."
  # RELEASE: bump url + sha256 + version on each tag
  url "https://files.pythonhosted.org/packages/source/q/quirk-scanner/quirk-scanner-0.0.0.tar.gz"
  # RELEASE: bump url + sha256 + version on each tag
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.11"
  depends_on "pipx"

  def install
    venv = virtualenv_create(libexec, "python3.11")
    venv.pip_install "quirk-scanner[all]==#{version}"
    bin.install_symlink Dir["#{libexec}/bin/quirk"]
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/quirk --version")
  end
end
