# DNP3 Master Example (C++ and Python)

A minimal DNP3 master (client) in C++ built on the [OpenDNP3](https://github.com/dnp3/opendnp3)
library and one in Python built on the [PyDNP3](https://github.com/Kitensum/pydnp3). It connects to an outstation over TCP, runs a periodic Class 0
integrity poll, and prints every received measurement to the console.

Local/remote link addresses, target IP, and port are all command-line
arguments, so you can quickly test both address orientations if you're
troubleshooting an addressing mismatch.

## 1. Install OpenDNP3 & PyDNP3

**OpenDNP3**
```bash
git clone https://github.com/dnp3/opendnp3
cd opendnp3
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
sudo cmake --install build
```

**PyDNP3**
```bash
git clone --recursive http://github.com/Kisensum/pydnp3
cd ~/pydnp3/deps
rm -rf pybind11
git clone --branch v2.11.1 --depth 1 https://github.com/pybind/pybind11.git
cd ~/pydnp3
rm -rf build
python3 setup.py install
```

## 2. Build this project (for main.cpp)

```bash
cmake -B build
cmake --build build --config Release
```

This produces the `dnp3_master` executable in `build/`.

## 3. Run

**C++**
```
./dnp3_master <ip> <port> <local_addr(master)> <remote_addr(outstation)> [poll_seconds]
```

Example, matching a config with Master Address = 2 and Outstation Address = 1:
```bash
./dnp3_master 170.0.100.15 20000 2 0 10
```

If the outstation never responds (link stays "Reset of Remote Link" with no
reply — the exact symptom in the earlier packet capture), try the addresses
swapped:
```bash
./dnp3_master 170.0.100.15 20000 0 2 10
```

**Python**
```
python3 master.py <ip> <port> <local_addr(master)> <remote_addr(outstation)> [poll_seconds]
```


## What "local" and "remote" mean here

- `local_addr` is **this master's own DNP3 address**. It is written into the
  **source** field of every outgoing link-layer frame.
- `remote_addr` is the **outstation's DNP3 address**. It is written into the
  **destination** field of every outgoing frame, and must exactly match the
  outstation's own configured local address, or the outstation will silently
  discard every frame (which looks identical to "not connected").

## Notes

- `PrintingSOEHandler` logs every measurement update (binary, analog,
  counter, etc.) to stdout as it arrives.
- `startupIntegrityClassMask = ClassField::AllClasses()` requests all classes
  (0/1/2/3) on the initial poll, mirroring the "Integratity Poll Interval"
  behavior seen in GUI-based DNP3 simulators.
- The periodic scan added via `AddScan` re-requests Class 0 (static/current
  values) every `poll_seconds` seconds.
- For production use you'll likely want to add command handling
  (`master->SendCommand(...)`) and a custom `ISOEHandler` instead of the
  built-in printing one, plus TLS if your outstation requires secure DNP3.
