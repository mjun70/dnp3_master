#!/usr/bin/env python3
"""
DNP3 Master (Client) example in Python, using the `pydnp3` bindings for
OpenDNP3 (https://github.com/ChargePoint/pydnp3, packaged on PyPI as
`dnp3-python`).

IMPORTANT: pydnp3 is a community-maintained pybind11 wrapper, not an
official Automatak/Step Function I/O project, and its own bundled C++
core can lag behind the "release" branch we used for the C++ example
earlier in this conversation. Class/method names below match the
well-established pydnp3 example pattern, but if you get an
AttributeError, run:

    python3 -c "from pydnp3 import asiodnp3; help(asiodnp3)"

...to see the exact names available in your installed version, and
adjust accordingly.

Mirrors the C++ example: same CLI args, same link-layer addressing
logic, same periodic class-scan polling.

Usage:
    python3 master.py <ip> <port> <local_addr> <remote_addr> [poll_seconds]

Example (Master=2, Outstation=1):
    python3 master.py 30.30.0.3 20000 2 1 30

If the outstation never responds, try swapping local/remote:
    python3 master.py 30.30.0.3 20000 1 2 30
"""

import sys

from pydnp3 import opendnp3, openpal, asiopal, asiodnp3


class SOEHandler(opendnp3.ISOEHandler):
    """
    Receives all measurement updates (Sequence-Of-Events) from the
    outstation and prints them. Override the Process() overloads you
    care about; the rest can just pass.
    """

    def Process(self, info, values):
        # `values` is an ICollection of Indexed<T> for whichever type
        # matched (Binary, Analog, Counter, etc). We just print the
        # raw collection; for typed access use values.Foreach(visitor).
        print(f"[SOE] header={info.gv} qualifier={info.qualifier} values={values}")

    def Start(self):
        pass

    def End(self):
        pass


class MasterApplication(opendnp3.IMasterApplication):
    """Callback hooks for master lifecycle/link events."""

    def AssignClassDuringStartup(self):
        return False

    def OnClose(self):
        print("[master] channel closed")

    def OnOpen(self):
        print("[master] channel opened")

    def OnReceiveIIN(self, iin):
        pass

    def OnTaskComplete(self, info):
        pass

    def OnTaskStart(self, task_type, task_id):
        pass


def main():
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} <ip> <port> <local_addr(master)> "
              f"<remote_addr(outstation)> [poll_seconds]")
        print(f"Example: {sys.argv[0]} 30.30.0.3 20000 2 1 30")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])
    local_addr = int(sys.argv[3])
    remote_addr = int(sys.argv[4])
    poll_seconds = int(sys.argv[5]) if len(sys.argv) >= 6 else 30

    print(f"Starting DNP3 master:")
    print(f"  Target:          {ip}:{port}")
    print(f"  Local (master):  {local_addr}")
    print(f"  Remote (outsta): {remote_addr}")
    print(f"  Poll interval:   {poll_seconds}s")
    print()

    # 1) Manager: owns the thread pool and top-level logging.
    manager = asiodnp3.DNP3Manager(1, asiodnp3.ConsoleLogger.Create())

    # 2) TCP client channel.
    channel = manager.AddTCPClient(
        "tcp-client",
        opendnp3.levels.NORMAL | opendnp3.levels.ALL_APP_COMMS,
        asiopal.ChannelRetry.Default(),
        ip,
        "0.0.0.0",  # local adapter, any
        port,
        asiodnp3.PrintingChannelListener.Create()
    )

    # 3) Master stack config: link-layer addressing + app-layer timeouts.
    stack_config = asiodnp3.MasterStackConfig()

    # LocalAddr  = this master's own DNP3 address (SOURCE in outgoing frames)
    # RemoteAddr = the outstation's DNP3 address (DESTINATION in outgoing
    #              frames; must match the outstation's own local address)
    stack_config.link.LocalAddr = local_addr
    stack_config.link.RemoteAddr = remote_addr

    stack_config.master.responseTimeout = openpal.TimeDuration().Seconds(5)
    stack_config.master.disableUnsolOnStartup = True

    # 4) Bind a master session to the channel.
    master = channel.AddMaster(
        "master",
        SOEHandler(),
        MasterApplication(),
        stack_config
    )

    # 5) Periodic Class 0/1/2/3 integrity poll, same as the C++ example's
    #    AddClassScan / Freya's "Integratity Poll Interval" field.
    master.AddClassScan(
        opendnp3.ClassField().AllClasses(),
        openpal.TimeDuration().Seconds(poll_seconds),
        SOEHandler()
    )

    # 6) Enable — starts the connection attempt and startup integrity poll.
    master.Enable()

    print("Master enabled. Press Enter to exit.")
    input()

    manager.Shutdown()


if __name__ == "__main__":
    main()
