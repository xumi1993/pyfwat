cmake_minimum_required(VERSION 3.14)
project(your_package LANGUAGES Fortran)

set(CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -O3")

set(SOURCE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/fksrc)

add_executable(compute_fk_injection_field
    ${SOURCE_PATH}/coupling_fk.f90
    ${SOURCE_PATH}/utils.f90
    ${SOURCE_PATH}/compute_fk_injection_field.f90
)

find_package(MPI REQUIRED)
target_link_libraries(compute_fk_injection_field PRIVATE MPI::MPI_Fortran)

install(TARGETS compute_fk_injection_field RUNTIME DESTINATION pyfwat)