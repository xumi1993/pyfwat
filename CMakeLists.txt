cmake_minimum_required(VERSION 3.14)
project(your_package LANGUAGES Fortran)

set(CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -O3")

set(SOURCE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/fksrc)

find_package(MPI REQUIRED)

set(app_sources
    # ${SOURCE_PATH}/compute_fk_receiver.f90
    ${SOURCE_PATH}/compute_fk_injection_field.f90
)

foreach(app_source ${app_sources})
    get_filename_component(app_name ${app_source} NAME_WE)
    add_executable(${app_name} ${app_source}
        ${SOURCE_PATH}/coupling_fk.f90
        ${SOURCE_PATH}/utils.f90
    )
    target_link_libraries(${app_name} PRIVATE MPI::MPI_Fortran)
    install(TARGETS ${app_name} RUNTIME DESTINATION pyfwat)

endforeach()
