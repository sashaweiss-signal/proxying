#!/usr/bin/env python3

import argparse
import subprocess
import os
import textwrap
import tempfile

class Args:
    def __init__(
        self,
        signal_root_path: str,
        script_paths: list[str],
        use_web: bool,
        skip_proxy_config: bool
    ):
        self.signal_root_path = signal_root_path
        self.script_paths = script_paths
        self.use_web = use_web
        self.skip_proxy_config = skip_proxy_config

    @classmethod
    def parse(cls) -> 'Args':
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''
                Start mitmproxy.

                If --script is given, will load the given path as a mitmproxy addon script.

                If --web-ui is given, will use mitmweb instead of mitmproxy to open a web UI for inspecting flows.

                If --no-network-proxy is given, will not automatically configure system network proxy settings.
                Potentially desirable if using this script with a physical device, as configuring the system network
                proxy is required when using this script with an iOS simulator.
            '''),
            usage="%(prog)s --signal-root <path-to-a-Signal-iOS-repo> [--script path-to-script] [--web-ui]"
        )

        parser.add_argument(
            "--signal-root",
            action="store",
            help="Path to the root of a Signal iOS repo.",
            required=True
        )

        parser.add_argument(
            "--script",
            action="append",
            help="Path to a mitmproxy addon script to load. May be passed multiple times."
        )
        parser.add_argument(
            "--web-ui",
            action='store_true',
            help="Open a web UI for inspecting requests."
        )
        parser.add_argument(
            "--no-network-proxy",
            action='store_true',
            help="Do not automatically configure the system network proxy settings. Useful if planning to proxy a physical device, instead of a simulator."
        )

        raw_args = parser.parse_args()

        signal_root_path = raw_args.signal_root
        script_path = raw_args.script
        use_web = raw_args.web_ui
        skip_proxy_config = raw_args.no_network_proxy

        return cls(
            signal_root_path,
            script_path,
            use_web,
            skip_proxy_config
        )



def get_signal_cert_path(signal_root_path: str) -> str:
    """
    Get a path to the Signal CA cert that the iOS app will pin.
    """

    return f"{signal_root_path}/SignalServiceKit/Resources/Certificates/signal-messenger.cer"


def replace_signal_ca_cert_with_mitmproxy(
    cert_path: str
) -> None:
    """
    Overwrite Signal's pinnned CA cert with `mitmproxy`'s CA cert. Optionally
    excludes the modified cert from `git`, to avoid accidentally committing the
    `mitmproxy` cert.
    """

    mitmproxy_cert_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")

    if not os.path.exists(mitmproxy_cert_path):
        raise Exception(
            f"Mitmproxy cert missing at {mitmproxy_cert_path}! Make sure mitmproxy has launched at least once, so it can generate certs."
        )

    run_command([
        "openssl",
        "x509",
        "-inform", "PEM",
        "-outform", "DER",
        "-in", mitmproxy_cert_path,
        "-out", cert_path
    ])


def reset_signal_ca_cert(cert_path: str) -> None:
    """
    Reset an overwritten Signal CA cert, and optionally re-add it to git.
    """

    run_command([
        "git", "checkout", cert_path
    ])


def make_signal_ca_cert_pem(
    cert_path: str,
    tmp_dir: str
) -> str:
    """
    Create a PEM-encoded copy of Signal's CA cert, to be used by `mitmproxy`. Returns
    the path at which the PEM cert can be found, which will be inside the given
    temp dir.
    """

    pem_string = get_command_output([
        "openssl",
        "x509",
        "-inform", "DER",
        "-outform", "PEM",
        "-in", cert_path
    ])

    pem_cert_path = f"{tmp_dir}/signal-messenger.pem"

    with open(pem_cert_path, "w") as f:
        f.write(pem_string)

    return pem_cert_path


def manage_proxy(args: list[str]):
    """
    Invoke the `manage_proxy` script with the given args.
    """

    path_to_manage_proxy = f"{os.path.dirname(__file__)}/manage_proxy"

    run_command([path_to_manage_proxy] + args)


def run_mitmproxy(args: Args, pem_signal_ca_cert_path: str):
    """
    Run mitmproxy, configuring as appropriate for the given args. Takes a PEM-encoded
    version of Signal's CA cert.
    """

    command_args = [
        "mitmweb" if args.use_web else "mitmproxy"
    ]

    if args.script_paths is not None:
        for script_path in args.script_paths:
            command_args += ["--scripts", script_path]

    # Need to tell mitmproxy to expect that the upstream servers are using
    # Signal's custom CA cert.
    command_args += [
        "--set",
        f"ssl_verify_upstream_trusted_ca={pem_signal_ca_cert_path}"
    ]

    run_command(command_args, silent=False)


def check_dep(dep_name: str):
    """
    Check that a given dependency is installed.
    """

    run_command([
        "which", dep_name
    ])


def run_command(args: list[str], silent: bool = True) -> None:
    """
    Run the given args as a command.
    """

    subprocess.run(
        args, check=True, capture_output=silent
    )


def get_command_output(args: list[str]) -> str:
    """
    Get the output of running the given command.
    """

    return subprocess.run(
        args, capture_output=True, encoding="utf8", check=True
    ).stdout.rstrip()


def main():
    check_dep("mitmproxy")
    check_dep("openssl")

    args = Args.parse()

    signal_cert_path = get_signal_cert_path(
        signal_root_path=args.signal_root_path
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        pem_signal_ca_cert_path = make_signal_ca_cert_pem(
            cert_path=signal_cert_path,
            tmp_dir=tmp_dir
        )

        # Do this after making the PEM, otherwise the PEM will be broken :)
        replace_signal_ca_cert_with_mitmproxy(cert_path=signal_cert_path)

        if not args.skip_proxy_config:
            manage_proxy(["set", "127.0.0.1", "8080"])

        run_mitmproxy(
            args=args,
            pem_signal_ca_cert_path=pem_signal_ca_cert_path
        )

        if not args.skip_proxy_config:
            manage_proxy(["disable"])

        reset_signal_ca_cert(signal_cert_path)


if __name__ == "__main__":
    main()
