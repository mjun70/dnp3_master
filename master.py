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

import sys, os

from pydnp3 import opendnp3, openpal, asiopal, asiodnp3

# --- Visitor Classes ---

class BinaryVisitor(opendnp3.IVisitorIndexedBinary):
    def __init__(self, info):
        super().__init__()
        self.info = info

    def OnValue(self, indexed_value):
        print(f"[SOE] Binary index={indexed_value.index} value={indexed_value.value.value}")

class BinaryOutputStatusVisitor(opendnp3.IVisitorIndexedBinaryOutputStatus):
    def __init__(self, info):
        super().__init__()
        self.info = info

    def OnValue(self, indexed_value):
        print(f"[SOE] BinaryOutputStatus index={indexed_value.index} value={indexed_value.value.value}")

class AnalogVisitor(opendnp3.IVisitorIndexedAnalog):
    def __init__(self, info):
        super().__init__()
        self.info = info

    def OnValue(self, indexed_value):
        print(f"[SOE] Analog index={indexed_value.index} value={indexed_value.value.value}")

class CounterVisitor(opendnp3.IVisitorIndexedCounter):
    def __init__(self, info):
        super().__init__()
        self.info = info

    def OnValue(self, indexed_value):
        print(f"[SOE] Counter index={indexed_value.index} value={indexed_value.value.value}")

class AnalogOutputStatusVisitor(opendnp3.IVisitorIndexedAnalogOutputStatus):
    def __init__(self, info):
        super().__init__()
        self.info = info

    def OnValue(self, indexed_value):
        print(f"[SOE] AnalogOutputStatus index={indexed_value.index} value={indexed_value.value.value}")
        
        
# --- SOE Handler ---

class SOEHandler(opendnp3.ISOEHandler):
    """
    Receives measurement updates (Sequence-Of-Events) from the outstation
    and routes them to the matching type visitor.
    """

    def Process(self, info, values):
        if isinstance(values, opendnp3.ICollectionIndexedBinary):
            values.Foreach(BinaryVisitor(info))
        elif isinstance(values, opendnp3.ICollectionIndexedBinaryOutputStatus):
            values.Foreach(BinaryOutputStatusVisitor(info))
        elif isinstance(values, opendnp3.ICollectionIndexedAnalog):
            values.Foreach(AnalogVisitor(info))
        elif isinstance(values, opendnp3.ICollectionIndexedCounter):
            values.Foreach(CounterVisitor(info))
        elif isinstance(values, opendnp3.ICollectionIndexedAnalogOutputStatus):
            values.Foreach(AnalogOutputStatusVisitor(info))

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

    # Construct these as named variables (not inline temporaries) and keep
    # them referenced for the lifetime of the program. Some pydnp3 builds
    # don't keep the Python-side callback object alive correctly via the
    # C++ shared_ptr holder, so an inline `SOEHandler()` can get garbage
    # collected out from under the stack once real callbacks start firing.
    soe_handler = SOEHandler()
    master_application = MasterApplication()

    # 4) Bind a master session to the channel.
    master = channel.AddMaster(
        "master",
        soe_handler,
        master_application,
        stack_config
    )

    # 5) Periodic Class 0/1/2/3 integrity poll, same as the C++ example's
    #    AddClassScan / Freya's "Integratity Poll Interval" field.
    master.AddClassScan(
        opendnp3.ClassField().AllClasses(),
        openpal.TimeDuration().Seconds(poll_seconds)
    )

    # 6) Enable — starts the connection attempt and startup integrity poll.
    master.Enable()

    print("Master enabled. Press Enter to exit.")
    input()

    # Explicitly tear down active DNP3 sessions first
    #master.Disable()
    #channel.Shutdown()

    # Stop thread manager
    #manager.Shutdown()

    # Bypass pybind11 C++ thread-join lock on exit
    os._exit(0)


if __name__ == "__main__":
    main()
