// DNP3 Master (Client) example using OpenDNP3
//
// Connects to an outstation over TCP, performs periodic integrity polls,
// and prints all received measurements to the console.
//
// Local/remote link addresses and the target IP/port are all set via
// command-line arguments so you can quickly test both address orientations
// (this was built after diagnosing a case where the master/outstation
// addresses were reversed on the wire vs. what was configured).
//
// Build: see CMakeLists.txt in this directory.
//
// Usage:
//   dnp3_master <ip> <port> <local_addr(master)> <remote_addr(outstation)> [poll_seconds]
//
// Example (matches the config discussed: Master=2, Outstation=1):
//   dnp3_master 30.30.0.3 20000 2 1 30
//
// If the outstation never responds, try swapping local/remote:
//   dnp3_master 30.30.0.3 20000 1 2 30

#include <opendnp3/DNP3Manager.h>
#include <opendnp3/channel/PrintingChannelListener.h>
#include <opendnp3/logging/LogLevels.h>
#include <opendnp3/master/DefaultMasterApplication.h>
#include <opendnp3/master/PrintingSOEHandler.h>
#include <opendnp3/master/PrintingCommandCallback.h>

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>

using namespace std;
using namespace opendnp3;

int main(int argc, char** argv)
{
    if (argc < 5)
    {
        cerr << "Usage: " << argv[0]
             << " <ip> <port> <local_addr(master)> <remote_addr(outstation)> [poll_seconds]\n";
        cerr << "Example: " << argv[0] << " 30.30.0.3 20000 2 1 30\n";
        return 1;
    }

    const string ip = argv[1];
    const uint16_t port = static_cast<uint16_t>(stoi(argv[2]));
    const uint16_t localAddr = static_cast<uint16_t>(stoi(argv[3]));
    const uint16_t remoteAddr = static_cast<uint16_t>(stoi(argv[4]));
    const unsigned int pollSeconds = (argc >= 6) ? static_cast<unsigned int>(stoi(argv[5])) : 30;

    cout << "Starting DNP3 master:\n"
         << "  Target:          " << ip << ":" << port << "\n"
         << "  Local (master):  " << localAddr << "\n"
         << "  Remote (outsta): " << remoteAddr << "\n"
         << "  Poll interval:   " << pollSeconds << "s\n\n";

    // 1) Create the manager. The first argument is the number of threads
    //    used to service the underlying ASIO event loop.
    const uint32_t FILTERS = levels::NORMAL | levels::ALL_COMMS;
    DNP3Manager manager(1, ConsoleLogger::Create());

    // 2) Create a TCP client channel. This is the outer "communication link"
    //    (Freya's "Communication Mode: TCP_IP_MODE" equivalent).
    auto channel = manager.AddTCPClient(
        "tcp-client",
        FILTERS,
        ChannelRetry::Default(),
        ip,
        "0.0.0.0", // local adapter to bind, 0.0.0.0 = any
        port,
        PrintingChannelListener::Create());

    // 3) Configure the master stack: link-layer addressing, timeouts, and
    //    application-layer behavior.
    MasterStackConfig config;

    // --- Link layer addressing ---
    // LocalAddr  = this master's own DNP3 address (sent as the SOURCE
    //              address in outgoing frames).
    // RemoteAddr = the outstation's DNP3 address (sent as the DESTINATION
    //              address in outgoing frames, and must match the value
    //              the outstation expects as its local address).
    config.link.LocalAddr = localAddr;
    config.link.RemoteAddr = remoteAddr;
    config.link.KeepAliveTimeout = TimeDuration::Seconds(60);
    config.link.Timeout = TimeDuration::Seconds(2);

    // --- Master application layer settings ---
    config.master.responseTimeout = TimeDuration::Seconds(5);
    config.master.disableUnsolOnStartup = true;
    config.master.startupIntegrityClassMask = ClassField::AllClasses();

    // --- Periodic integrity poll (Class 0/1/2/3), similar to Freya's
    //     "Integratity Poll Interval - class 0,1,2,3" field ---
    config.master.tasks.startupIntegrityClassMask = ClassField::AllClasses();

    // 4) Add the master to the channel.
    //    PrintingSOEHandler prints every received measurement (analog,
    //    binary, counter, etc.) to stdout.
    //    DefaultMasterApplication provides default callback behavior.
    auto master = channel->AddMaster(
        "master",
        PrintingSOEHandler::Create(),
        DefaultMasterApplication::Create(),
        config);

    // 5) Schedule a recurring integrity poll (Class 0 read = full static
    //    data poll), equivalent to Freya's periodic integrity poll.
    auto integrityPoll = master->AddScan(
        Header::AllObjects(GroupVariation::Group60Var1), // Class 0 - static data
        TimeDuration::Seconds(pollSeconds));

    // 6) Enable the master. This starts the connection attempt and, once
    //    connected, performs the startup integrity poll automatically.
    master->Enable();

    cout << "Master enabled. Press Enter to exit.\n";
    cout << "Watching for 'LINK STATE' and comms in the console output above...\n\n";

    string line;
    getline(cin, line);

    // 7) Clean shutdown.
    manager.Shutdown();

    return 0;
}
