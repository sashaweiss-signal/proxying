# Signal iOS and `mitmproxy`

This directory contains code to use [mitmproxy][mitmproxy-home] to proxy Signal iOS, allowing a developer to inspect, modify, respond to, or otherwise work with requests made by the app.

Beyond simply viewing "bytes on the wire", `mitmproxy` also supports flexible "addons" that may be useful during development. See [below](#building-custom-mitmproxy-addons) for more.

## One-time setup

Install `mitmproxy` as described [here][mitmproxy-install].

Then, install the `mitmproxy` CA certificate. The easiest way to do this (described [here][mitmproxy-certs]) is to run `mitmproxy`, configure proxy settings to run your test device/simulator through `mitmproxy` (see [below](#configuring-network-proxy-settings)), and visit the magic domain `mitm.it`, which provides helpful links.

> iOS simulators share network proxy settings with their host system, and so if you plan to use `mitmproxy` with a simulator your whole machine machine will need to proxy through `mitmproxy`. Consequently, if you are planning to use an iOS simulator make sure to install the CA cert for both the simulator and your host machine.

## Proxying Signal iOS

### Start `mitmproxy`

Signal clients pin a Signal-specific CA cert when communicating with Signal services. Consequently, when putting `mitmproxy` between Signal iOS and Signal services there is some configuration required.

To configure and start `mitmproxy` for proxying Signal iOS, simply run:

```sh
; ./start-proxy.py
```

> Installing `mitmproxy` also installs `mitmweb`, which provides similar request inspection capabilities as `mitmproxy`, but through a browser-based UI instead of an interactive terminal app. If you'd prefer to use the web UI, pass `--web-ui` to the `start-proxy.py` script.

This will do the following:

1. Replace the `signal-messenger.cer` CA cert included in the iOS repo (and built into the app) with `mitmproxy`'s (locally-generated, specific-to-your-machine) CA cert, so `mitmproxy` can inspect requests.

2. Create a temporary copy of Signal's CA cert, formatted such that it can be passed to `mitmproxy` so it can communicate with Signal services.

3. Configure the system's network settings to use `mitmproxy` as an HTTP(S) proxy. (This can be skipped by passing `--no-network-proxy`.)

4. Configure and run `mitmproxy`.

> Since `mitmproxy` is interactive, the script will not complete until you exit `mitmproxy`. Once `mitmproxy` shuts down, the script will clean up any file or configuration changes it made.
>
> While `start-proxy.py` is running, you may notice in `git` that `signal-messenger.cer` has been modified, per (1) above.

### Run Signal

Once `mitmproxy` is configured and running, build and run Signal as normal - you should see requests running through `mitmproxy`!

## Configuring network proxy settings

Once `mitmproxy` is running, we need to forward network traffic through it.

> As a convenience, you can use the `manage_proxy` script included here to quickly set/enable/disable system proxy settings on your machine:
>
> ```sh
> ; manage_proxy set 127.0.0.1 8080
> ; manage_proxy disable
> ; manage_proxy enable
> ```

### For an iOS simulator

iOS simulators share network settings with their host machine. Therefore, to proxy a simulator, you will need to configure your host's network to go through `mitmproxy`.

> This means that all your local traffic will go through `mitmproxy`, which in turn means you will need to install `mitmproxy`'s CA cert on the host machine in addition to in the simulator. See above.

> `start-proxy.py` will, by default, automatically configure system network proxy settings to forward all traffic on the local machine through `mitmproxy`.

### For a physical device

If you're trying to proxy a physical device, you'll need to route it through the machine running `mitmproxy`. For example, that might look like finding your machine's IP on the local network, and using that IP in the device's network settings.

> If using a physical device, you may want to pass `--no-network-proxy` to `start-proxy.py` to skip the configuration of your local machine's network settings.

## Building custom `mitmproxy` addons

`mitmproxy` has a robust and flexible [addon system][mitmproxy-addons] in which users can write Python scripts that can perform actions while `mitmproxy` is running, such as "return a preconfigured response for requests to a given domain".

For example, you might want to test what happens in response to a 404 while making a particular request. If that scenario requires state that is difficult to set up, an addon script can intercept the request in question and respond with a 404 instead of allowing the request to continue to the service.

To load an addon, pass `--script <path-to-script>` as an argument to `start-proxy.py`. You may pass `--script` multiple times, to load multiple addons.

```sh
; ./start-proxy.py --script my_addon.py
```

[mitmproxy-home]: https://mitmproxy.org
[mitmproxy-addons]: https://docs.mitmproxy.org/stable/addons-overview
[mitmproxy-install]: https://docs.mitmproxy.org/stable/overview-installation
[mitmproxy-certs]: https://docs.mitmproxy.org/stable/concepts-certificates/#quick-setup
