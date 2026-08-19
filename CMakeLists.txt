cmake_minimum_required(VERSION 3.10)
project(dnp3_master CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Expects opendnp3 to be installed (via vcpkg, conan, or built from source
# and installed with `cmake --install .`). See README.md for instructions.
find_package(DNP3 REQUIRED)

add_executable(dnp3_master main.cpp)

target_link_libraries(dnp3_master PRIVATE opendnp3)
