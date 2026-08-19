cmake_minimum_required(VERSION 3.10)
project(dnp3_master CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# This build of opendnp3 only installed the target export set
# (opendnp3-export*.cmake) and not a full find_package-compatible
# opendnp3-config.cmake, so we include the export file directly instead
# of calling find_package(). This defines the opendnp3::opendnp3 IMPORTED
# target with its include dirs and library baked in.
#
# Override this path with -DOPENDNP3_EXPORT_FILE=... if yours lives
# elsewhere (check with: find / -iname 'opendnp3-export.cmake' 2>/dev/null).
set(OPENDNP3_EXPORT_FILE "/usr/local/lib/cmake/opendnp3-export.cmake"
    CACHE FILEPATH "Path to opendnp3's generated export file")

if(NOT EXISTS "${OPENDNP3_EXPORT_FILE}")
    message(FATAL_ERROR
        "Could not find opendnp3 export file at: ${OPENDNP3_EXPORT_FILE}\n"
        "Run: find / -iname 'opendnp3-export.cmake' 2>/dev/null\n"
        "and pass the correct path with -DOPENDNP3_EXPORT_FILE=<path>")
endif()

include("${OPENDNP3_EXPORT_FILE}")

add_executable(dnp3_master main.cpp)

target_link_libraries(dnp3_master PRIVATE opendnp3::opendnp3)
