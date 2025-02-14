program write_injection_field
  use mpi
  use fk_injection
  implicit none
  integer, parameter :: THREE = 3
  ! integer, parameter :: NGLLMID = (NGLLSQUARE + 1) / 2
  integer :: ier, ip, ib, igll, ilayer,nlines, nb, np, nargs
  character(len=256) :: fn
  real(kind=CUSTOM_REAL) :: ray_p,Tg,DF_FK
  integer :: ii, kk, iim1, iip1, iip2, it_tmp
  real(kind=CUSTOM_REAL) :: cs1,cs2,cs3,cs4,w

  real(kind=CUSTOM_REAL), parameter :: TOL_ZERO_TAKEOFF = 1.e-14

  real(kind=CUSTOM_REAL) :: zmid, ztop
  real(kind=CUSTOM_REAL) :: time_t

  call MPI_Init(ier)
  if (ier /= 0 ) stop 'Error initializing MPI'
  call MPI_Comm_rank(MPI_COMM_WORLD, myrank, ier)

  ! get num of arguments
  nargs = iargc()
  ! read local_path from command line
  if (nargs == 2) then
   call getarg(1, local_path)
   call getarg(2, FKMODEL_FILE)
  endif

  call ReadFKModelInput()

  ! converts origin point Z to reference framework depth for FK,
  ! where top of lower half-space has to be at z==0
  zz0 = zz0 - Z_REF_for_FK

  ! converts to rad
  phi_FK   = phi_FK * PI/180.d0    ! azimuth
  theta_FK = theta_FK * PI/180.d0  ! take-off

  ! ray parameter p (according to Snell's law: sin(theta1)/v1 ==
  ! sin(theta2)/v2)
  if (type_kpsv_fk == 1) then
    ! P-wave
    ray_p = sin(theta_FK)/alpha_FK(nlayer)    ! for vp (i.e., alpha)
  else if (type_kpsv_fk == 2) then
    ! SV-wave
    ray_p = sin(theta_FK)/beta_FK(nlayer)     ! for vs (i.e., beta)
  endif

  ! note: vertical incident (theta==0 -> p==0) is not handled.
  !       here, it limits ray parameter p to a very small value to handle
  !       the calculations
  if (abs(ray_p) < TOL_ZERO_TAKEOFF) ray_p = sign(TOL_ZERO_TAKEOFF,ray_p)

  ! maximum period
  Tg  = 1.d0 / ff0

  call find_size_of_working_arrays(deltat, freq_sampling_fk, tmax_fk, &
                                   NF_FOR_STORING, &
                                   NF_FOR_FFT, NPOW_FOR_INTERP, NP_RESAMP, &
                                   DF_FK)

  ! user output
  if (myrank == 0) then
    write(IMAIN,*) '  computed FK parameters:'
    write(IMAIN,*) '    frequency sampling rate        = ', freq_sampling_fk,"(Hz)"
    write(IMAIN,*) '    number of frequencies to store = ', NF_FOR_STORING
    write(IMAIN,*) '    number of frequencies for FFT  = ', NF_FOR_FFT
    write(IMAIN,*) '    power of 2 for FFT             = ', NPOW_FOR_INTERP
    write(IMAIN,*)
    write(IMAIN,*) '    simulation time step           = ', deltat,"(s)"
    write(IMAIN,*) '    total simulation length        = ', NSTEP*deltat,"(s)"
    write(IMAIN,*)
    write(IMAIN,*) '    FK time resampling rate        = ', NP_RESAMP
    write(IMAIN,*) '    new time step for F-K          = ', NP_RESAMP * deltat,"(s)"
    write(IMAIN,*) '    new time window length         = ', tmax_fk,"(s)"
    write(IMAIN,*)
    write(IMAIN,*) '    frequency step for F-K         = ', DF_FK,"(Hz)"
    call flush_IMAIN()
  endif

  ! safety check with number of simulation time steps
  if (NSTEP/NP_RESAMP > NF_FOR_STORING + NP_RESAMP) then
    if (myrank == 0) then
      print *,'Error: FK time window length ',tmax_fk,' and NF_for_storing ',NF_FOR_STORING
      print *,'       are too small for chosen simulation length with NSTEP = ',NSTEP
      print *
      print *,'       you could use a smaller NSTEP <= ',NF_FOR_STORING*NP_RESAMP
      print *,'       or'
      print *,'       increase FK window length larger than ',(NSTEP/NP_RESAMP - NP_RESAMP) * NP_RESAMP * deltat
      print *,'       to have a NF for storing  larger than ',(NSTEP/NP_RESAMP - NP_RESAMP)
    endif
    write(0, *) 'Invalid FK setting'
    stop 1
  endif

  ! safety check
  if (NP_RESAMP == 0) then
    if (myrank == 0) then
      print *,'Error: FK resampling rate ',NP_RESAMP,' is invalid for frequency sampling rate ',freq_sampling_fk
      print *,'       and the chosen simulation DT = ',deltat
      print *
      print *,'       you could use a higher frequency sampling rate>',1./(deltat)
      print *,'       (or increase the time stepping size DT if possible)'
    endif
    write(0, *) 'Invalid FK setting'
    stop 1

  endif

  ! limits resampling sizes
  if (NP_RESAMP > 10000) then
    if (myrank == 0) then
      print *,'Error: FK resampling rate ',NP_RESAMP,' is too high for frequency sampling rate ',freq_sampling_fk
      print *,'       and the chosen simulation DT = ',deltat
      print *
      print *,'       you could use a higher frequency sampling rate>',1./(10000*deltat)
      print *,'       (or increase the time stepping size DT if possible)'
    endif
    write(0, *) 'Invalid FK setting'
    stop 1
  endif
  call MPI_BARRIER(MPI_COMM_WORLD, ier)

  call read_abs_normal()
  call MPI_BARRIER(MPI_COMM_WORLD, ier)

  np = size(xx)

  allocate(Veloc_FK(THREE, np, -NP_RESAMP:NF_FOR_STORING+NP_RESAMP), &
           Tract_FK(THREE, np, -NP_RESAMP:NF_FOR_STORING+NP_RESAMP))
  Veloc_FK = 0.0_CUSTOM_REAL
  Tract_FK = 0.0_CUSTOM_REAL

  call FK(alpha_FK, beta_FK, mu_FK, h_FK, nlayer, &
          Tg, ray_p, phi_FK, xx0, yy0, zz0, &
          tt0, deltat, NSTEP, np, &
          type_kpsv_fk, NF_FOR_STORING, NPOW_FOR_FFT,  NP_RESAMP, DF_FK)

  write(fn, "(a,'/proc',i6.6,'_sol_axisem')")&
      trim(local_path), myrank
  open(88, file=trim(fn), form="unformatted", action="write")
  ! if (myrank == 0) open(99, file='injection_veloc', form='formatted', action='write')
  ! data
  do it_tmp = 1,NSTEP
        ! FK coupling
        !! find indices
        ! example:
        !   np_resamp = 1 and it = 1,2,3,4,5,6, ..
        !   --> ii = 1,2,3,4,5,6,..
        !   np_resamp = 2 and it = 1,2,3,4,5,6, ..
        !   --> ii = 1,1,2,2,3,3,..
    ii = floor( real(it_tmp + NP_RESAMP - 1) / real( NP_RESAMP))
        ! example:
        !       kk = 1,2,1,2,1,2,,..
    kk = it_tmp - (ii-1) * NP_RESAMP
        ! example:
        !       w = 0,1/2,0,1/2,..
    w = dble(kk-1) / dble(NP_RESAMP)

    ! Cubic spline values
    cs4 = w*w*w/6.d0
    cs1 = 1.d0/6.d0 + w*(w-1.d0)/2.d0 - cs4
    cs3 = w + cs1 - 2.d0*cs4
    cs2 = 1.d0 - cs1 - cs3 - cs4

    ! interpolation indices
    iim1 = ii-1        ! 0,..
    iip1 = ii+1        ! 2,..
    iip2 = ii+2        ! 3,..

    v_FK = cs1*Veloc_FK(:,:,iim1)+cs2*Veloc_FK(:,:,ii)+cs3*Veloc_FK(:,:,iip1)&
             +cs4*Veloc_FK(:,:,iip2)
    t_FK = cs1*Tract_FK(:,:,iim1)+cs2*Tract_FK(:,:,ii)&
             +cs3*Tract_FK(:,:,iip1)+cs4*Tract_FK(:,:,iip2)
    write(88) v_FK, t_FK
    ! ! time
    ! time_t = (it_tmp-1) * deltat - tt0
    ! if (myrank == 0) write(99, *) time_t, v_FK(1,1), v_FK(2,1), v_FK(3,1)
  enddo
  close(88)
  close(99)
  call MPI_Finalize(ier)
end program write_injection_field
