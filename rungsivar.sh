#!/bin/bash

#SBATCH -J gsivar
#SBATCH -o gsivar.o%J
#SBATCH -A da-cpu
#SBATCH -q batch
#SBATCH -p hercules
#SBATCH --nodes=10
#SBATCH --ntasks=160
#SBATCH --cpus-per-task=5
#SBATCH -t 00:30:00

set -ax
date

ntasks=160
ppn=16
threads=5

export NODES=$(( $ntasks / $ppn ))
npe_node_max=$(( $ppn * $threads ))
npe_gsi=$ntasks

# Set GSI path
HOMEgsi=/work2/noaa/da/rtreadon/git/gsi/hercules/develop

# Load modules
module purge
module use ${HOMEgsi}/modulefiles
module load gsi_hercules.intel
module list


# Set environment variables
export OMP_STACKSIZE=2G
export OMP_NUM_THREADS=$threads
unset I_MPI_EXTRA_FILESYSTEM
ulimit -s unlimited

# Set experiment name and analysis date
adate=2026061000
exp=test.${adate}


# Set YES to use background from EMC parallel
# NO = take from /com/gfs/para
use_emc_para=YES

# Set YES to use ensemble, NO=pure 3dvar
DOHYBVAR=NO

# Set YES to run 4denvar.  NO=3denvar or hybrid 3dvar
DO4DENSVAR=NO

# Set YES to use smoothed enkf forecasts for hybrid/envar
SMOOTH_ENKF=NO

# Set YES to use radstat file to initialize bc
USE_RADSTAT=NO


# Set YES to generate diagnostic files
GENDIAG="YES"
DIAG_SUFFIX=""
CDATE=$adate
DIAG_COMPRESS=YES
COMPRESS=gzip
UNCOMPRESS=gunzip
DIAG_TARBALL=YES
DIAG_DIR="./"
CHGRP_CMD="chgrp rstprod"


# Set DO_CALC_INCREMENT flag
#  NO means GSI writes increment files
#  YES (default) means GSI writes analysis files
DO_CALC_INCREMENT="NO"


# Select gdas or gfs data dump
dumpobs=${CDUMP:-gdas}


# Set size of ensemble
ENS_NUM_ANAL=40


# Set path/file for gsi executable
gsiexec=${HOMEgsi}/install/bin/gsi.x
catexec=${ncdiag_ROOT}/bin/ncdiag_cat_serial.x


# Set the JCAP resolution which you want.
export JCAP=192
export JCAP_B=384
export LEVS=127


# Set runtime and save directories
PTMP=/work/noaa/stmp
DATA=${PTMP}/${LOGNAME}/tmp_gsi/${exp}
SAVDIR=${PTMP}/${LOGNAME}/out_gsi/${exp}


# Specify GSI fixed field
fixgsi=${HOMEgsi}/fix
fixcrtm=$CRTM_FIX


# Set variables used in script
#   CLEAN up $DATA when finished (YES=remove, NO=leave alone)
#   ncp is cp replacement, currently keep as /bin/cp

CLEAN=NO
export wc=${wc:-/usr/bin/wc}
ncpc=/bin/cp
ncpl="ln -fs"
NLN="ln -fs"

# Given the requested resolution, set dependent resolution parameters
if [[ "$JCAP" = "1534" ]]; then
   export LONA=3072
   export LATA=1536
   export DELTIM=120
elif [[ "$JCAP" = "1148" ]]; then
   export LONA=2304
   export LATA=1152
   export DELTIM=120
elif [[ "$JCAP" = "878" ]]; then
   export LONA=1760
   export LATA=880
   export DELTIM=120
elif [[ "$JCAP" = "766" ]]; then
   export LONA=1536
   export LATA=768
   export DELTIM=450
elif [[ "$JCAP" = "574" ]]; then
   export LONA=1152
   export LATA=576
   export DELTIM=450
elif [[ "$JCAP" = "384" ]]; then
   export LONA=1536
   export LATA=768
   export DELTIM=189
elif [[ "$JCAP" = "382" ]]; then
   export LONA=768
   export LATA=384
   export DELTIM=189   
elif [[ "$JCAP" = "192" ]]; then
    export LONA=768
    export LATA=384
    export DELTIM=450
elif [[ "$JCAP" = "254" ]]; then
   export LONA=512
   export LATA=256
   export DELTIM=450
elif [[ "$JCAP" = "126" ]]; then
   export LONA=384
   export LATA=190
   export DELTIM=600
elif [[ "$JCAP" = "62" ]]; then
   export LONA=192
   export LATA=94
   export DELTIM=1200
else
   echo "INVALID JCAP = $JCAP"
   exit
fi
export NLON=$LONA
export NLAT=$((${LATA}+2))


# Given the analysis date, compute the date from which the
# first guess comes.  Extract cycle and set prefix and suffix
# for guess and observation data files
PDYa=`echo $adate | cut -c1-8`
cyca=`echo $adate | cut -c9-10`
gdate=`date +%Y%m%d%H -d "${adate:0:8} ${adate:8:2} - 6 hours"`
PDYg=`echo $gdate | cut -c1-8`
cycg=`echo $gdate | cut -c9-10`
PDY=$PDYa
cyc=$cyca

prefix_obs=${dumpobs}.t${cyca}z
prefix_ges=gdas.t${cycg}z
prefix_ens=enkfgdas.t${cycg}z
suffix=tm00.bufr_d

dumpges=gdas
dumpanl=$dumpobs

if [[ "$use_emc_para" = "YES" ]]; then
##   DMPDIR==/work/noaa/rstprod/dump
##   datobs=$DMPDIR/$dumpanl.$PDYa/$cyca/atmos
   
   COMROOT=/work/noaa/stmp/rtreadon/COMROOT/prgsi
   datobs=$COMROOT/$dumpanl.$PDYa/${cyca}/obs
   datges=$COMROOT/$dumpges.$PDYg/${cycg}/model/atmos/history
   datbc=$COMROOT/$dumpges.$PDYg/${cycg}/analysis/atmos
   datanl=$COMROOT/$dump
else
   COMROOT=/lfs/h1/ops/prod/com
   DMPDIR=$COMROOT/obsproc/v1.2
   COMROOT=$COMROOT/gfs/v16.3
   datobs=$DMPDIR/$dumpobs.${PDYa}/$cyca/atmos
   datges=$COMROOT/$dumpges.${PDYg}/$cycg/atmos
   datanl=$COMROOT/$dumpanl.${PDYa}/$cyca/atmos

fi
datens=$COMROOT/enkfgdas.$PDYg/${cycg}


# Create $DATA
rm -rf $DATA
mkdir -p $DATA
cd $DATA
rm -rf core*


# Make gsi namelist

# CO2 namelist and file decisions
ICO2=${ICO2:-0}
if [ $ICO2 -gt 0 ] ; then
#  Copy co2 files to $DATA
   co2dir=${CO2DIR:-$fixgsi}
   yyyy=$(echo ${CDATE:-$adate}|cut -c1-4)
   rm ./global_co2_data.txt
   co2=$co2dir/global_co2.gcmscl_$yyyy.txt
   if [ -s $co2 ] ; then
      $ncpc $co2 ./global_co2_data.txt
   fi
   if [ ! -s ./global_co2_data.txt ] ; then
      echo "\./global_co2_data.txt" not created
##    exit 1
   fi
fi

# Initalize extra GSI namelist variables to blank string
SETUP=""
GRIDOPTS=""
BKGERR=""
ANBKGERR=""
JCOPTS=""
STRONGOPTS=""
OBSQC=""
OBSINPUT=""
SUPERRAD=""
LAGDATA=""
HYBRIDENSEMBLE=""
RR_CLDSURF=""
CHEM=""
SINGLEOB=""
NSST=""


# Set increment flags
DO_CALC_INCREMENT=${DO_CALC_INCREMENT:-"YES"}
DO_CALC_ANALYSIS=${DO_CALC_ANALYSIS:-"NO"}
INCREMENTS_TO_ZERO=${INCREMENTS_TO_ZERO:-"'NONE'"}
INCVARS_ZERO_STRAT=${INCVARS_ZERO_STRAT:-"'NONE'"}
incvars_efold=${incvars_efold:-5}


# determine if writing or calculating increment
SETUP_INC=""
if [ $DO_CALC_INCREMENT = "YES" ]; then
  write_fv3_increment=".false."
  SETUP_INC="write_fv3_incr=$write_fv3_increment,"
else
  write_fv3_increment=".true."
##INCREMENTS_TO_ZERO="'liq_wat_inc','icmr_inc','rwmr_inc','snmr_inc','grle_inc'"
  WRITE_INCR_ZERO="incvars_to_zero= $INCREMENTS_TO_ZERO"
##INCREMENTS_TO_ZERO_STRAT="'sphum_inc','liq_wat_inc','icmr_inc','rwmr_inc','snmr_inc','grle_inc'"
  WRITE_INCR_ZERO_STRAT="incvars_zero_strat=$INCREMENTS_TO_ZERO_STRAT"
  incvars_efold="5"
  SETUP_INC="write_fv3_incr=$write_fv3_increment,$WRITE_INCR_ZERO,$WRITE_INCR_ZERO_STRAT,incvars_efold=$incvars_efold,"
fi


# Set obs bin time
##nhr_obsbin=1
nhr_obsbin=${nhr_obsbin:-3}

# Set GSI namelist variables based on above flags
if [[ "$DOHYBVAR" = "NO" ]]; then
   STRONGOPTS="tlnmc_option=1,"
fi

# HYBRIDENSEMBLE namelist below set up for C384
JCOPTS_4DVAR=""
HYBRIDENSEMBLE_TEST=""
if [[ "$DOHYBVAR" = "YES" ]]; then
##  ens_fast_read=".false."
    ens_fast_read=${ens_fast_read:-".true."}
    ensemble_dir='./ensemble_data/'
    export ensemble_path=${ensemble_dir:-./}
    export beta_s=${beta_s:-0.125}
    export s_ens_v=${s_ens_v:-"-0.8"}
    readin_localization=".false."
    export readin_localization=${readin_localization:-".true."}
    HYBRIDENSEMBLE="l_hyb_ens=.true.,n_ens=$ENS_NUM_ANAL,beta_s0=$beta_s,readin_beta=.false.,s_ens_h=800.,s_ens_v=${s_ens_v},generate_ens=.false.,uv_hyb_ens=.true.,jcap_ens=382,nlat_ens=386,nlon_ens=768,aniso_a_en=.false.,jcap_ens_test=382,readin_localization=${readin_localization},oz_univ_static=.false.,ensemble_path='${ensemble_path}',ens_fast_read=$ens_fast_read,write_ens_sprd=.true.,$HYBRIDENSEMBLE_TEST"
fi
if [[ "$nhr_obsbin" = "1" ]]; then
    JCOPTS_4DVAR="ljc4tlevs=.true.,"
fi

# Turn off generation of diagnostic files for GFS run
SETUPGFS=""
if [[ "$dumpobs" = "gfs" ]]; then
  SETUPGFS="diag_rad=.false.,diag_pcp=.false.,diag_conv=.false.,diag_ozone=.false.,diag_aero=.false.,write_diag(3)=.false.,niter(2)=100,"
  USE_RADSTAT=NO
fi

# Turn on NSST
SETUP_NSST="tzr_qc=1,sfcnst_comb=.true.,"
NSST="nst_gsi=3,nstinfo=4,zsea1=0,zsea2=0,fac_dtl=1,fac_tsl=1,"

SETUP_4DVAR=""
STRONGOPTS_4DVAR=""
if [[ "$DO4DENSVAR" = "YES" ]]; then
   SETUP_4DVAR="l4densvar=.true.,ens_nstarthr=3,nhr_obsbin=$nhr_obsbin,nhr_assimilation=6,lwrite4danl=.true.,"  # 1 hourly, 7 analysis
   JCOPTS_4DVAR="ljc4tlevs=.true.,"
   STRONGOPTS_4DVAR="tlnmc_option=3,"    # TLNMC on total increment over all time levels (if in 4D EnVar mode)
## STRONGOPTS_4DVAR="tlnmc_option=2,"    # TLNMC applied to increment in center of window
## STRONGOPTS_4DVAR="tlnmc_option=4,"    # TLNMC on static contribution to increment ONLY for any EnVar mode
## STRONGOPTS_4DVAR="tlnmc_option=0,"    # TLNMC off
fi

##export verbose=".true."
export verbose=${verbose:-".false."}
export imp_physics=8
export imp_physics=${imp_physics:-11}  # 11=GFDL,  8=Thompson
export lupp=${lupp:-".true."}
export lrun_subdirs=${lrun_subdirs:-".true."}
export subdirs_path=${DIAG_DIR:-"./"}
export use_readin_anl_sfcmask=".true."
export use_readin_anl_sfcmask=${use_readin_anl_sfcmask:-".false."}
export use_gfs_ncio=".true."
export use_gfs_nemsio=${use_gfs_nemsio:-".false."}
export use_gfs_ncio=${use_gfs_ncio:-".false."}
export netcdf_diag=".true."
export binary_diag=${binary_diag:-".false."}
export netcdf_diag=${netcdf_diag:-".false."}
export nvqc=".true."
export nvqc=${nvqc:-".false."}
export vqc=${vqc:-".false."}
export hub_norm=".true."
export hub_norm=${hub_norm:-".false."}
##export qc_noirjaco3_pole=".true."
export qc_noirjaco3_pole=${qc_noirjaco3_pole:-".false."}
##export lobsdiag_forenkf=".true."
export lobsdiag_forenkf=${lobsdiag_forenkf:-".false."}
##export nhr_anal="3,6,9"
export nhr_anal=${nhr_anal:-"6"}
cnvw_option=${cnvw_option:-".false."}
cao_check=${cao_check:-".true."}
export ta2tb=${ta2tb:-".true."}
crtm_coeffs="./crtm_coeffs/"
export crtm_coeffs=${crtm_coeffs:-./}
##cwoption=0
export cwoption=${cwoption:-3}
cwcoveqqcov=".false."
cwcoveqqcov=${cwcoveqqcov:-".false."}
hofx_2m_sfcfile=".false."
hofx_2m_sfcfile=${hofx_2m_sfcfile:-"true"}
##export qoption=1
export qoption=${qoption:-2}
export factqmin=${factqmin:-0.5}
export factqmax=${factqmax:-0.0002}
export optconv=${optconv:-0.06}
export AIRS_CADS=${AIRS_CADS:-".false."}
export IASI_CADS=${IASI_CADS:-".false."}
export CRIS_CADS=${CRIS_CADS:-".false."}

if [ $netcdf_diag = ".true." ] ; then
   DIAG_SUFFIX="${DIAG_SUFFIX}.nc4"
fi

if [ $nvqc = ".true." ] ; then
    vqc=".false."
fi
if [ $vqc = ".true." ]; then
    nvqc=".false."
fi

# Set file format for guess and analysis
format="nemsio"
SETUP_NCIO=""
if [ $use_gfs_ncio = ".true." ]; then
    format="nc"
    SETUP_NCIO="use_gfs_ncio=${use_gfs_ncio},"
fi

SETUP_TEST=""
BKGERR_TEST=""
JCOPTS_TEST=""
STRONGOPTS_TEST=""
OBSQC_TEST=""


export SETUP_TEST="miter=1,niter(1)=50,factqmin=0.0,factqmax=0.0,write_diag(2)=.true.,thin4d=.false.,l4densvar=.false.,lwrite4danl=.false.,nhr_obsbin=3,"
export BKGERR_TEST="bkgv_flowdep=.false.,"
export JCOPTS_TEST="ljcpdry=.false.,bamp_jcpdry=0.0,ljc4tlevs=.false.,"
export STRONGOPTS_TEST="tlnmc_option=0,"
export OBSQC_TEST="aircraft_t_bc=.false.,upd_aircraft=.false.,cleanup_tail=.false.,noiqc=.false.,nvqc=.false.,hub_norm=.false.,"

write_fv3_increment=".true."
INCREMENTS_TO_ZERO="'NONE','NONE','NONE','NONE','NONE'"
WRITE_INCR_ZERO="incvars_to_zero= $INCREMENTS_TO_ZERO"
INCREMENTS_TO_ZERO_STRAT="'NONE','NONE','NONE','NONE','NONE','NONE'"
WRITE_INCR_ZERO_STRAT="incvars_zero_strat=$INCREMENTS_TO_ZERO_STRAT"
incvars_efold="5"
SETUP_INC="write_fv3_incr=$write_fv3_increment,$WRITE_INCR_ZERO,$WRITE_INCR_ZERO_STRAT,incvars_efold=$incvars_efold,"


# Collect settings above into variables used below
SETUP="$SETUP_4DVAR $SETUP_NSST $SETUPGFS $SETUP_INC $SETUP_NCIO $SETUP_TEST"
BKGERR="$BKGERR_TEST"
JCOPTS="$JCOPTS_4DVAR $JCOPTS_TEST"
STRONGOPTS="$STRONGOPTS_4DVAR $STRONGOPTS_TEST"
OBSQC="$OBSQC $OBSQC_TEST"


# Set fixed files
#   berror   = forecast model background error statistics
#   specoef  = CRTM spectral coefficients
#   trncoef  = CRTM transmittance coefficients
#   emiscoef = CRTM coefficients for IR sea surface emissivity model
#   aerocoef = CRTM coefficients for aerosol effects
#   cldcoef  = CRTM coefficients for cloud effects
#   satinfo  = text file with information about assimilation of brightness temperatures
#   satangl  = angle dependent bias correction file (fixed in time)
#   pcpinfo  = text file with information about assimilation of prepcipitation rates
#   ozinfo   = text file with information about assimilation of ozone data
#   errtable = text file with obs error for conventional data (optional)
#   convinfo = text file with information about assimilation of conventional data
#   bufrtable= text file ONLY needed for single obs test (oneobstest=.true.)
#   bftab_sst= bufr table for sst ONLY needed for sst retrieval (retrieval=.true.)
#   aeroinfo = text file with information about assimilation of aerosol data

anavinfo=$fixgsi/global_anavinfo.l${LEVS}.txt
berror=$fixgsi/global_berror.l${LEVS}y${NLAT}.nc
locinfo=$fixgsi/global_hybens_info.l${LEVS}.txt
satinfo=$fixgsi/global_satinfo.txt
scaninfo=$fixgsi/global_scaninfo.txt
satangl=$fixgsi/global_satangbias.txt
pcpinfo=$fixgsi/global_pcpinfo.txt
ozinfo=$fixgsi/global_ozinfo.txt
convinfo=$fixgsi/global_convinfo.txt
vqcdat=$fixgsi/vqctp001.dat
insituinfo=$fixgsi/global_insituinfo.txt
errtable=$fixgsi/prepobs_errtable.global
blacklst=$fixgsi/rejectlist_global.txt
aeroinfo=$fixgsi/global_aeroinfo.txt
atmsbeaminfo=$fixgsi/atms_beamwidth.txt
cloudyinfo=$fixgsi/cloudy_radiance_info.txt

airsclddet=$fixgsi/AIRS_CLDDET.NL
crisclddet=$fixgsi/CRIS_CLDDET.NL
iasiclddet=$fixgsi/IASI_CLDDET.NL

emiscoef_IRwater=$fixcrtm/Nalli.IRwater.EmisCoeff.bin
emiscoef_IRice=$fixcrtm/NPOESS.IRice.EmisCoeff.bin
emiscoef_IRland=$fixcrtm/NPOESS.IRland.EmisCoeff.bin
emiscoef_IRsnow=$fixcrtm/NPOESS.IRsnow.EmisCoeff.bin
emiscoef_VISice=$fixcrtm/NPOESS.VISice.EmisCoeff.bin
emiscoef_VISland=$fixcrtm/NPOESS.VISland.EmisCoeff.bin
emiscoef_VISsnow=$fixcrtm/NPOESS.VISsnow.EmisCoeff.bin
emiscoef_VISwater=$fixcrtm/NPOESS.VISwater.EmisCoeff.bin
emiscoef_MWwater=$fixcrtm/FASTEM6.MWwater.EmisCoeff.bin
aercoef=$fixcrtm/AerosolCoeff.bin

if (( imp_physics == 8 )); then 
    cldcoef=$fixcrtm/CloudCoeff.Thompson08.-109z-1.bin
elif (( imp_physics == 11 )); then 
    cldcoef=$fixcrtm/CloudCoeff.GFDLFV3.-109z-1.bin
else
    echo "FATAL ERROR: INVALID imp_physics = ${imp_physics}"
    export err=1
    exit $err
fi

# Only need this file for single obs test
bufrtable=$fixgsi/prepobs_prep.bufrtable

# Only need this file for sst retrieval
bftab_sst=$fixgsi/bufrtab.012


# Create GSI namelist
rm -f gsiparm.anl
cat <<EOF > gsiparm.anl
 &SETUP
   miter=2,
   niter(1)=50,niter(2)=150,
   niter_no_qc(1)=25,niter_no_qc(2)=0,
   write_diag(1)=.true.,write_diag(2)=.false.,write_diag(3)=.true.,
   qoption=${qoption},
   gencode=0,deltim=$DELTIM,
   factqmin=$factqmin,factqmax=$factqmax
   iguess=-1,
   oneobtest=.false.,retrieval=.false.,l_foto=.false.,
   use_pbl=.false.,use_compress=.true.,nsig_ext=45,gpstop=50.,commgpstop=45.,commgpserrinf=1.0,
   use_gfs_nemsio=${use_gfs_nemsio},lrun_subdirs=${lrun_subdirs},
   use_readin_anl_sfcmask=${use_readin_anl_sfcmask},
   crtm_coeffs_path='${crtm_coeffs}',
   newpc4pred=.true.,adp_anglebc=.true.,angord=4,passive_bc=.true.,use_edges=.false.,
   diag_precon=.true.,step_start=1.e-3,emiss_bc=.true.,thin4d=.true.,cwoption=${cwoption},
   verbose=${verbose},imp_physics=$imp_physics,lupp=$lupp,cnvw_option=$cnvw_option,cao_check=${cao_check},
   binary_diag=$binary_diag,netcdf_diag=$netcdf_diag,
   lobsdiag_forenkf=$lobsdiag_forenkf,
   nhr_anal=$nhr_anal,nhr_obsbin=$nhr_obsbin,
   ta2tb=${ta2tb},optconv=${optconv},
   $SETUP
 /
 &GRIDOPTS
   JCAP_B=$JCAP_B,JCAP=$JCAP,NLAT=$NLAT,NLON=$NLON,nsig=$LEVS,
   regional=.false.,
   $GRIDOPTS
 /
 &BKGERR
   vs=0.7,
   hzscl=1.7,0.8,0.5,
   hswgt=0.45,0.3,0.25,
   bw=0.0,norsp=4,
   bkgv_flowdep=.true.,bkgv_rewgtfct=1.5,
   bkgv_write=.false.,
   cwcoveqqcov=${cwcoveqqcov},
   $BKGERR   
 /
 &ANBKGERR
   anisotropic=.false.,
   $ANBKGERR
 /
 &JCOPTS
   ljcdfi=.false.,alphajc=0.0,ljcpdry=.true.,bamp_jcpdry=5.0e7,
   $JCOPTS   
 /
 &STRONGOPTS
   tlnmc_option=2,nstrong=1,nvmodes_keep=8,period_max=6.,period_width=1.5,
   baldiag_full=.false.,baldiag_inc=.false.,
   $STRONGOPTS   
 /
 &OBSQC
   dfact=0.75,dfact1=3.0,noiqc=.true.,oberrflg=.false.,c_varqc=0.02,
   use_poq7=.true.,qc_noirjaco3_pole=${qc_noirjaco3_pole},vqc=$vqc,nvqc=$nvqc,hub_norm=$hub_norm,
   aircraft_t_bc=.true.,biaspredt=1.0e5,upd_aircraft=.true.,cleanup_tail=.true.,
   tcp_width=70.0,tcp_ermax=7.35,airs_cads=${AIRS_CADS},cris_cads=${CRIS_CADS},
   iasi_cads=${IASI_CADS},blacklst=${blacklst},
   $OBSQC
 /
&OBS_INPUT
  dmesh(1)=145.0,dmesh(2)=150.0,dmesh(3)=100.0,dmesh(4)=50.0,time_window_max=3.0,
  hofx_2m_sfcfile=${hofx_2m_sfcfile},
  
/
OBS_INPUT::
!  dfile          dtype       dplat       dsis                dval    dthin dsfcalc
   prepbufr       ps          null        ps                  0.0     0     0
   prepbufr       t           null        t                   0.0     0     0
   prepbufr_profl t           null        t                   0.0     0     0
   hdobbufr       t           null        t                   0.0     0     0
   prepbufr       q           null        q                   0.0     0     0
   prepbufr_profl q           null        q                   0.0     0     0
   hdobbufr       q           null        q                   0.0     0     0
   prepbufr       pw          null        pw                  0.0     0     0
   prepbufr       uv          null        uv                  0.0     0     0
   prepbufr_profl uv          null        uv                  0.0     0     0
   wbbufr         t           null        t                   0.0     0     0
   wbbufr         q           null        q                   0.0     0     0
   wbbufr         uv          null        uv                  0.0     0     0
   sdbufr         ps          null        ps                  0.0     0     0
   sdbufr         t           null        t                   0.0     0     0
   sdbufr         q           null        q                   0.0     0     0
   sdbufr         uv          null        uv                  0.0     0     0
   satwndbufr     uv          null        uv                  0.0     0     0
   hdobbufr       uv          null        uv                  0.0     0     0
   prepbufr       spd         null        spd                 0.0     0     0
   hdobbufr       spd         null        spd                 0.0     0     0
   prepbufr       dw          null        dw                  0.0     0     0
   radarbufr      rw          null        rw                  0.0     0     0
   nsstbufr       sst         nsst        sst                 0.0     0     0
   gpsrobufr      gps_bnd     null        gps                 0.0     0     0
   ssmirrbufr     pcp_ssmi    dmsp        pcp_ssmi            0.0    -1     0
   tmirrbufr      pcp_tmi     trmm        pcp_tmi             0.0    -1     0
   sbuvbufr       sbuv2       n16         sbuv8_n16           0.0     0     0
   sbuvbufr       sbuv2       n17         sbuv8_n17           0.0     0     0
   sbuvbufr       sbuv2       n18         sbuv8_n18           0.0     0     0
   gimgrbufr      goes_img    g11         imgr_g11            0.0     1     0
   gimgrbufr      goes_img    g12         imgr_g12            0.0     1     0
   airsbufr       airs        aqua        airs_aqua           0.0     1     1
   amsuabufr      amsua       n15         amsua_n15           0.0     1     1
   amsuabufr      amsua       n18         amsua_n18           0.0     1     1
   amsuabufr      amsua       metop-a     amsua_metop-a       0.0     1     1
   airsbufr       amsua       aqua        amsua_aqua          0.0     1     1
   amsubbufr      amsub       n17         amsub_n17           0.0     1     1
   mhsbufr        mhs         n18         mhs_n18             0.0     1     1
   mhsbufr        mhs         metop-a     mhs_metop-a         0.0     1     1
   ssmitbufr      ssmi        f15         ssmi_f15            0.0     1     0
   amsrebufr      amsre_low   aqua        amsre_aqua          0.0     1     0
   amsrebufr      amsre_mid   aqua        amsre_aqua          0.0     1     0
   amsrebufr      amsre_hig   aqua        amsre_aqua          0.0     1     0
   ssmisbufr      ssmis       f16         ssmis_f16           0.0     1     0
   ssmisbufr      ssmis       f17         ssmis_f17           0.0     1     0
   ssmisbufr      ssmis       f18         ssmis_f18           0.0     1     0
   gsnd1bufr      sndrd1      g12         sndrD1_g12          0.0     1     0
   gsnd1bufr      sndrd2      g12         sndrD2_g12          0.0     1     0
   gsnd1bufr      sndrd3      g12         sndrD3_g12          0.0     1     0
   gsnd1bufr      sndrd4      g12         sndrD4_g12          0.0     1     0
   gsnd1bufr      sndrd1      g11         sndrD1_g11          0.0     1     0
   gsnd1bufr      sndrd2      g11         sndrD2_g11          0.0     1     0
   gsnd1bufr      sndrd3      g11         sndrD3_g11          0.0     1     0
   gsnd1bufr      sndrd4      g11         sndrD4_g11          0.0     1     0
   gsnd1bufr      sndrd1      g13         sndrD1_g13          0.0     1     0
   gsnd1bufr      sndrd2      g13         sndrD2_g13          0.0     1     0
   gsnd1bufr      sndrd3      g13         sndrD3_g13          0.0     1     0
   gsnd1bufr      sndrd4      g13         sndrD4_g13          0.0     1     0
   iasibufr       iasi        metop-a     iasi_metop-a        0.0     1     1
   gomebufr       gome        metop-a     gome_metop-a        0.0     2     0
   omibufr        omi         aura        omi_aura            0.0     2     0
   sbuvbufr       sbuv2       n19         sbuv8_n19           0.0     0     0
   amsuabufr      amsua       n19         amsua_n19           0.0     1     1
   mhsbufr        mhs         n19         mhs_n19             0.0     1     1
   tcvitl         tcp         null        tcp                 0.0     0     0
   seviribufr     seviri      m08         seviri_m08          0.0     1     0
   seviribufr     seviri      m09         seviri_m09          0.0     1     0
   seviribufr     seviri      m10         seviri_m10          0.0     1     0
   seviribufr     seviri      m11         seviri_m11          0.0     1     0
   amsuabufr      amsua       metop-b     amsua_metop-b       0.0     1     1
   mhsbufr        mhs         metop-b     mhs_metop-b         0.0     1     1
   iasibufr       iasi        metop-b     iasi_metop-b        0.0     1     1
   gomebufr       gome        metop-b     gome_metop-b        0.0     2     0
   atmsbufr_skip  atms        npp         atms_npp            0.0     1     1
   atmsbufr       atms        n20         atms_n20            0.0     1     1
   atmsbufr_skip  atms        n21         atms_n21            0.0     1     1
   crisbufr       cris        npp         cris_npp            0.0     1     0
   crisfsbufr     cris-fsr    npp         cris-fsr_npp        0.0     1     0
   crisfsbufr     cris-fsr    n20         cris-fsr_n20        0.0     1     0
   crisfsbufr     cris-fsr    n21         cris-fsr_n21        0.0     1     0
   gsnd1bufr      sndrd1      g14         sndrD1_g14          0.0     1     0
   gsnd1bufr      sndrd2      g14         sndrD2_g14          0.0     1     0
   gsnd1bufr      sndrd3      g14         sndrD3_g14          0.0     1     0
   gsnd1bufr      sndrd4      g14         sndrD4_g14          0.0     1     0
   gsnd1bufr      sndrd1      g15         sndrD1_g15          0.0     1     0
   gsnd1bufr      sndrd2      g15         sndrD2_g15          0.0     1     0
   gsnd1bufr      sndrd3      g15         sndrD3_g15          0.0     1     0
   gsnd1bufr      sndrd4      g15         sndrD4_g15          0.0     1     0
   oscatbufr      uv          null        uv                  0.0     0     0
   mlsbufr        mls30       aura        mls30_aura          0.0     0     0
   avhambufr      avhrr       metop-a     avhrr3_metop-a      0.0     4     0
   avhpmbufr      avhrr       n18         avhrr3_n18          0.0     4     0
   avhambufr      avhrr       metop-b     avhrr3_metop-b      0.0     4     0
   avhambufr      avhrr       metop-c     avhrr3_metop-c      0.0     4     0
   avhpmbufr      avhrr       n19         avhrr3_n19          0.0     4     0
   amsr2bufr      amsr2       gcom-w1     amsr2_gcom-w1       0.0     3     0
   gmibufr        gmi         gpm         gmi_gpm             0.0     1     0
   saphirbufr     saphir      meghat      saphir_meghat       0.0     3     0
   ahibufr        ahi         himawari8   ahi_himawari8       0.0     1     0
   abibufr        abi         g16         abi_g16             0.0     1     0
   abibufr        abi         g17         abi_g17             0.0     1     0
   abibufr        abi         g18         abi_g18             0.0     1     0
   abibufr        abi         g19         abi_g19             0.0     1     0
   rapidscatbufr  uv          null        uv                  0.0     0     0
   ompsnpbufr     ompsnp      npp         ompsnp_npp          0.0     0     0
   ompslpbufr     ompslp      npp         ompslp_npp          0.0     0     0
   ompstcbufr     ompstc8     npp         ompstc8_npp         0.0     2     0
   ompsnpbufr     ompsnp      n20         ompsnp_n20          0.0     0     0
   ompstcbufr     ompstc8     n20         ompstc8_n20         0.0     2     0
   amsuabufr      amsua       metop-c     amsua_metop-c       0.0     1     1
   mhsbufr        mhs         metop-c     mhs_metop-c         0.0     1     1
   iasibufr       iasi        metop-c     iasi_metop-c        0.0     1     1
   sstviirs       viirs-m     npp         viirs-m_npp         0.0     4     0
   sstviirs       viirs-m     j1          viirs-m_j1          0.0     4     0
   ahibufr        ahi         himawari9   ahi_himawari9       0.0     1     0
   sstviirs       viirs-m     j2          viirs-m_j2          0.0     4     0
   ompsnpbufr     ompsnp      n21         ompsnp_n21          0.0     0     0
   ompstcbufr     ompstc8     n21         ompstc8_n21         0.0     2     0
   gomebufr       gome        metop-c     gome_metop-c        0.0     2     0
::
  &SUPEROB_RADAR
   $SUPERRAD
 /
  &LAG_DATA
   $LAGDATA
 /
  &HYBRID_ENSEMBLE
   $HYBRIDENSEMBLE
 /
  &RAPIDREFRESH_CLDSURF
   dfi_radar_latent_heat_time_period=30.0,
   $RR_CLDSURF
 /
  &CHEM
   $CHEM
 /
  &NST
   $NSST
 /
 &SINGLEOB_TEST
   maginnov=0.1,magoberr=0.1,oneob_type='t',
   oblat=5.,oblon=180.,obpres=850.,obdattim=${adate},
   obhourset=0.,
   $SINGLEOB
 /
EOF


# Copy executable and fixed files to $DATA
$ncpc $gsiexec ./gsi.x

$ncpc $anavinfo ./anavinfo
$ncpc $berror   ./berror_stats
$ncpc $locinfo  ./hybens_info
$ncpc $satinfo  ./satinfo
$ncpc $scaninfo ./scaninfo
$ncpc $pcpinfo  ./pcpinfo
$ncpc $ozinfo   ./ozinfo
$ncpc $convinfo ./convinfo
$ncpc $vqcdat   ./vqctp001.dat
$ncpc $insituinfo ./insituinfo
$ncpc $errtable ./errtable
$ncpc $blacklst ./blacklist
$ncpc $aeroinfo ./aeroinfo
$ncpc $atmsbeaminfo ./atms_beamwidth.txt
$ncpc $cloudyinfo   ./cloudy_radiance_info.txt

$ncpc $bufrtable ./prepobs_prep.bufrtable
$ncpc $bftab_sst ./bftab_sstphr

$ncpc $airsclddet ./AIRS_CLDDET.NL
$ncpc $crisclddet ./CRIS_CLDDET.NL
$ncpc $iasiclddet ./IASI_CLDDET.NL

#If using correlated error, get the covariance files
if grep -q "Rcov" $anavinfo ;
then
  if ls ${fixgsi}/Rcov* 1> /dev/null 2>&1;
  then
    $ncpc ${fixgsi}/Rcov* $DATA

#   Correlated error utlizes mkl lapack.  Found it necesary to fix the
#   number of mkl threads to ensure reproducible results independent
#   of the job configuration.
    export MKL_NUM_THREADS=1

  else
    echo "Warning: Satellite error covariance files are missing."
    echo "Check for the required Rcov files in " $ANAVINFO
    exit 1
  fi
fi

# Diagnostic files
# if requested, link GSI diagnostic file directories for use later
if [ "$DIAG_DIR" != "./" ]; then
    if [ $GENDIAG = "YES" ] ; then
	if [ $lrun_subdirs = ".true." ] ; then
	    if [ -d $DIAG_DIR ]; then
		rm -rf $DIAG_DIR
	    fi
	    for pe in $(seq 1 $npe_gsi); do
		pem1=$((pe-1))
		pedir="dir."$(printf %04i $pem1)
		mkdir -p $DIAG_DIR/$pedir
		$NLN $DIAG_DIR/$pedir $pedir
	    done
	else
	    echo "lrun_subdirs must be true; exit with error"
	    exit 2
	fi
    fi
fi

# Copy CRTM coefficient files based on entries in satinfo file
mkdir -p ${crtm_coeffs}
for file in `awk '{if($1!~"!"){print $1}}' satinfo | sort | uniq` ;do
   $ncpl $fixcrtm/${file}.SpcCoeff.bin ${crtm_coeffs}/${file}.SpcCoeff.bin
   $ncpl $fixcrtm/${file}.TauCoeff.bin ${crtm_coeffs}/${file}.TauCoeff.bin
done
$ncpl $fixcrtm/amsua_metop-a_v2.SpcCoeff.bin ${crtm_coeffs}/amsua_metop-a_v2.SpcCoeff.bin

$ncpl $emiscoef_IRwater  ${crtm_coeffs}/Nalli.IRwater.EmisCoeff.bin
$ncpl $emiscoef_IRice    ${crtm_coeffs}/NPOESS.IRice.EmisCoeff.bin
$ncpl $emiscoef_IRsnow   ${crtm_coeffs}/NPOESS.IRsnow.EmisCoeff.bin
$ncpl $emiscoef_IRland   ${crtm_coeffs}/NPOESS.IRland.EmisCoeff.bin
$ncpl $emiscoef_VISice   ${crtm_coeffs}/NPOESS.VISice.EmisCoeff.bin
$ncpl $emiscoef_VISland  ${crtm_coeffs}/NPOESS.VISland.EmisCoeff.bin
$ncpl $emiscoef_VISsnow  ${crtm_coeffs}/NPOESS.VISsnow.EmisCoeff.bin
$ncpl $emiscoef_VISwater ${crtm_coeffs}/NPOESS.VISwater.EmisCoeff.bin
$ncpl $emiscoef_MWwater  ${crtm_coeffs}/FASTEM6.MWwater.EmisCoeff.bin
$ncpl $aercoef           ${crtm_coeffs}/AerosolCoeff.bin
$ncpl $cldcoef           ${crtm_coeffs}/CloudCoeff.bin

# Copy observational data to $DATA
##$ncpl $datobs/${prefix_obs}.prepbufr                ./prepbufr
##$ncpl $datobs/${prefix_obs}.prepbufr.acft_profiles  ./prepbufr_profl
##$ncpl $datobs/${prefix_obs}.nsstbufr                ./nsstbufr
##$ncpl $datanl/${prefix_obs}.syndata.tcvitals.tm00   ./tcvitl
##$ncpl $datobs/${prefix_obs}.gpsro.${suffix}         ./gpsrobufr
##$ncpl $datobs/${prefix_obs}.satwnd.${suffix}        ./satwndbufr
##$ncpl $datobs/${prefix_obs}.hdob.${suffix}          ./hdobbufr
####$ncpl $datobs/${prefix_obs}.saldrn.${suffix}        ./sdbufr
####$ncpl $datobs/${prefix_obs}.gsbpfl.${suffix}        ./wbbufr

##$ncpl $datobs/${prefix_obs}.osbuv8.${suffix}        ./sbuvbufr
##$ncpl $datobs/${prefix_obs}.gome.${suffix}          ./gomebufr
##$ncpl $datobs/${prefix_obs}.omi.${suffix}           ./omibufr
####$ncpl $datobs/${prefix_obs}.mls.${suffix}           ./mlsbufr
##$ncpl $datobs/${prefix_obs}.ompsn8.${suffix}        ./ompsnpbufr
##$ncpl $datobs/${prefix_obs}.ompst8.${suffix}        ./ompstcbufr
##$ncpl $datobs/${prefix_obs}.ompslp.${suffix}        ./ompslpbufr

##$ncpl $datobs/${prefix_obs}.goesfv.${suffix}        ./gsnd1bufr
##$ncpl $datobs/${prefix_obs}.airsev.${suffix}        ./airsbufr
##$ncpl $datobs/${prefix_obs}.sevcsr.${suffix}        ./seviribufr
##$ncpl $datobs/${prefix_obs}.saphir.${suffix}        ./saphirbufr
##$ncpl $datobs/${prefix_obs}.avcsam.${suffix}        ./avhambufr
##$ncpl $datobs/${prefix_obs}.avcspm.${suffix}        ./avhpmbufr
##$ncpl $datobs/${prefix_obs}.mtiasi.${suffix}        ./iasibufr
##$ncpl $datobs/${prefix_obs}.esiasi.${suffix}        ./iasibufrears
##$ncpl $datobs/${prefix_obs}.iasidb.${suffix}        ./iasibufr_db
##$ncpl $datobs/${prefix_obs}.crisf4.${suffix}        ./crisfsbufr
##$ncpl $datobs/${prefix_obs}.escrsf.${suffix}        ./crisfsbufrears
##$ncpl $datobs/${prefix_obs}.crsfdb.${suffix}        ./crisfsbufr_db
##$ncpl $datobs/${prefix_obs}.ahicsr.${suffix}        ./ahibufr
##$ncpl $datobs/${prefix_obs}.gsrcsr.${suffix}        ./abibufr
##$ncpl $datobs/${prefix_obs}.sstvcw.${suffix}        ./sstviirs

##$ncpl $datobs/${prefix_obs}.1bmhs.${suffix}         ./mhsbufr
##$ncpl $datobs/${prefix_obs}.1bmsu.${suffix}         ./msubufr
##$ncpl $datobs/${prefix_obs}.gmi1cr.${suffix}        ./gmibufr
##$ncpl $datobs/${prefix_obs}.ssmit.${suffix}         ./ssmitbufr
##$ncpl $datobs/${prefix_obs}.ssmisu.${suffix}        ./ssmisbufr
##$ncpl $datobs/${prefix_obs}.1bamua.${suffix}        ./amsuabufr
##$ncpl $datobs/${prefix_obs}.esamua.${suffix}        ./amsuabufrears
##$ncpl $datobs/${prefix_obs}.amuadb.${suffix}        ./amsuabufr_db
##$ncpl $datobs/${prefix_obs}.1bamub.${suffix}        ./amsubbufr
##$ncpl $datobs/${prefix_obs}.esamub.${suffix}        ./amsubbufrears
##$ncpl $datobs/${prefix_obs}.amubdb.${suffix}        ./amsubbufr_db

$ncpl $datobs/${prefix_obs}.atms.${suffix}          ./atmsbufr

##$ncpl $datobs/${prefix_obs}.atmsdb.${suffix}        ./atmsbufr_db
##$ncpl $datobs/${prefix_obs}.esatms.${suffix}        ./atmsbufrears

# Do not process
## $ncpl $datobs/${prefix_obs}.amsre.${suffix}         ./amsrebufr
## $ncpl $datobs/${prefix_obs}.amsr2.tm00.bufr_d       ./amsr2bufr
## $ncpl $datobs/${prefix_obs}.hrs3db.${suffix}        ./hirs3bufr_db
## $ncpl $datobs/${prefix_obs}.1bhrs4.${suffix}        ./hirs4bufr
## $ncpl $datobs/${prefix_obs}.1bhrs2.${suffix}        ./hirs2bufr
## $ncpl $datobs/${prefix_obs}.1bhrs3.${suffix}        ./hirs3bufr
## $ncpl $datobs/${prefix_obs}.eshrs3.${suffix}        ./hirs3bufrears
## $ncpl $datobs/${prefix_obs}.hrs3db.${suffix}        ./hirs3bufr_db             

# Copy bias correction, atmospheric and surface files
$ncpl $datbc/${prefix_ges}.abias.txt                   ./satbias_in
$ncpl $datbc/${prefix_ges}.abias_pc.txt                ./satbias_pc
$ncpl $datbc/${prefix_ges}.abias_air.txt               ./aircftbias_in

##$ncpl $datges/${prefix_ges}.sfc.f003.${format}         ./sfcf03
$ncpl $datges/${prefix_ges}.sfc.f006.${format}         ./sfcf06
##$ncpl $datges/${prefix_ges}.sfc.f009.${format}         ./sfcf09

##$ncpl $datges/${prefix_ges}.atm.f003.${format}         ./sigf03
$ncpl $datges/${prefix_ges}.atm.f006.${format}         ./sigf06
##$ncpl $datges/${prefix_ges}.atm.f009.${format}         ./sigf09

if [[ "$DO4DENSVAR" = "YES" || "$nhr_obsbin" = "1" ]]; then
   for fh in $(seq 3 $nhr_obsbin 9); do
      $ncpl $datges/${prefix_ges}.sfcf00${fh}.${format}       ./sfcf0${fh}
      $ncpl $datges/${prefix_ges}.atmf00${fh}.${format}       ./sigf0${fh}
   done
fi

if [[ "$DOHYBVAR" = "YES" ]]; then
  enkf_suffix=""
  if [[ "$SMOOTH_ENKF" = "YES" ]]; then  
     enkf_suffix="s"
  fi
  flist="06"
  if [[ "$DO4DENSVAR" = "YES" ]]; then
     flist="03 06 09"
     if [[ "$nhr_obsbin" = "1" ]]; then
        flist="03 04 05 06 07 08 09"
     fi
  fi
  mkdir -p $ensemble_path
  for fh in $flist; do
    sigens=${prefix_ens}.atm.f0${fh}${enkf_suffix}.${format}
    imem=1
    while [[ $imem -le $ENS_NUM_ANAL ]]; do
       member="mem"`printf %03i $imem`
       if [[ "$use_emc_para" = "YES" ]]; then
          $ncpl $datens/$member/model/atmos/history/$sigens ${ensemble_path}sigf${fh}_ens_${member}
       else
          $ncpl $datens/$member/$sigens ${ensemble_path}sigf${fh}_ens_${member}
       fi
       (( imem = $imem + 1 ))
    done
  done
fi

if [[ "${use_readin_anl_sfcmask}" = ".true." ]]; then
   $ncpl $datens/ensstat/model/atmos/history/${prefix_ens}.ensmean.sfc.f006.${format} ./sfcf06_anlgrid
fi

# If requested, copy and de-tar guess radstat file
if [[ $USE_RADSTAT = YES ]]; then
    ln -fs $datbc/${prefix_ges}.radstat.tar ./radstat.gdas
    listdiag=`tar xvf radstat.gdas | cut -d' ' -f2 | grep _ges`
    for type in $listdiag; do
	diag_file=`echo $type | cut -d',' -f1`
	fname=`echo $diag_file | cut -d'.' -f1`
	date=`echo $diag_file | cut -d'.' -f2`
	$UNCOMPRESS $diag_file
	fnameanl=$(echo $fname|sed 's/_ges//g')
	mv $fname.$gdate.nc4 $fnameanl
done

fi

# Run gsi under Parallel Operating Environment (poe) on NCEP IBM

APRUN="srun -l --export=ALL -n $ntasks"
date
$APRUN $DATA/gsi.x < gsiparm.anl > stdout 2>&1
rc=$?
date

cat fort.2* > $dumpobs.t${cyca}z.gsistat

if [[ "$GENDIAG" = "NO" ]] ; then
  date
  exit
fi

# Save output
mkdir -p $SAVDIR
cat stdout fort.2* > $SAVDIR/stdout.anl.$adate
cat fort.2*        > $SAVDIR/${prefix_obs}.gsistat
cat fort.2*        > $SAVDIR/gsistat.$dumpobs.$adate
$ncpc siganl          $SAVDIR/gfnanl.$dumpobs.$adate
$ncpc satbias_out     $SAVDIR/biascr.$dumpobs.$adate
$ncpc satbias_pc.out  $SAVDIR/biascr_pc.$dumpobs.$adate
$ncpc satbias_out.int $SAVDIR/biascr.int.$dumpobs.$adate

CNVSTAT=$SAVDIR/cnvstat.gdas.$adate
PCPSTAT=$SAVDIR/pcpstat.gdas.$adate
OZNSTAT=$SAVDIR/oznstat.gdas.$adate
RADSTAT=$SAVDIR/radstat.gdas.$adate

rm -f $CNVSTAT
rm -f $PCPSTAT
rm -f $OZNSTAT
rm -f $RADSTAT


cd $DATA    # we should already be in $DATA, but extra cd to be sure.
rm -rf diag_*

echo "before GENDIAG= $GENDIAG at `date`"

# If requested, generate diagnostic files
if [ $GENDIAG = "YES" ] ; then

   # cd to DIAG_DIR
   cd $DIAG_DIR

   # Set up lists and variables for various types of diagnostic files.
   ntype=3

   diagtype[0]="conv conv_gps conv_ps conv_pw conv_q conv_sst conv_t conv_tcp conv_uv conv_spd"
   diagtype[1]="pcp_ssmi_dmsp pcp_tmi_trmm"
   diagtype[2]="sbuv2_n16 sbuv2_n17 sbuv2_n18 sbuv2_n19 gome_metop-a gome_metop-b gome_metop-c omi_aura mls30_aura ompsnp_npp ompstc8_npp ompslp_npp ompsnp_n20 ompstc8_n20 ompslp_n20 ompsnp_n21 ompstc8_n21 ompslp_n21"
   diagtype[3]="hirs2_n14 msu_n14 sndr_g08 sndr_g11 sndr_g12 sndr_g13 sndr_g08_prep sndr_g11_prep sndr_g12_prep sndr_g13_prep sndrd1_g11 sndrd2_g11 sndrd3_g11 sndrd4_g11 sndrd1_g12 sndrd2_g12 sndrd3_g12 sndrd4_g12 sndrd1_g13 sndrd2_g13 sndrd3_g13 sndrd4_g13 sndrd1_g14 sndrd2_g14 sndrd3_g14 sndrd4_g14 sndrd1_g15 sndrd2_g15 sndrd3_g15 sndrd4_g15 hirs3_n15 hirs3_n16 hirs3_n17 amsua_n15 amsua_n16 amsua_n17 amsub_n15 amsub_n16 amsub_n17 hsb_aqua airs_aqua amsua_aqua imgr_g08 imgr_g11 imgr_g12 imgr_g14 imgr_g15 ssmi_f13 ssmi_f15 hirs4_n18 hirs4_metop-a amsua_n18 amsua_metop-a mhs_n18 mhs_metop-a amsre_low_aqua amsre_mid_aqua amsre_hig_aqua ssmis_f16 ssmis_f17 ssmis_f18 ssmis_f19 ssmis_f20 iasi_metop-a hirs4_n19 amsua_n19 mhs_n19 seviri_m08 seviri_m09 seviri_m10 seviri_m11 cris_npp cris-fsr_npp cris-fsr_n20 cris-fsr_n21 atms_npp atms_n20 atms_n21 hirs4_metop-b amsua_metop-b mhs_metop-b iasi_metop-b avhrr_metop-b avhrr_n18 avhrr_n19 avhrr_metop-a amsr2_gcom-w1 gmi_gpm saphir_meghat ahi_himawari8 ahi_himawari9 abi_g16 abi_g17 abi_g18 abi_g19 amsua_metop-c mhs_metop-c iasi_metop-c avhrr_metop-c viirs-m_j1 viirs-m_j2"

   diaglist[0]=listcnv
   diaglist[1]=listpcp
   diaglist[2]=listozn
   diaglist[3]=listrad

   diagfile[0]=$CNVSTAT
   diagfile[1]=$PCPSTAT
   diagfile[2]=$OZNSTAT
   diagfile[3]=$RADSTAT

   numfile[0]=0
   numfile[1]=0
   numfile[2]=0
   numfile[3]=0

   # Set diagnostic file prefix based on lrun_subdirs variable
   if [ $lrun_subdirs = ".true." ]; then
      prefix=" dir.*/"
   else
      prefix="pe*"
   fi

   if [ $USE_CFP = "YES" ]; then
      rm $DATA/diag.sh $DATA/mp_diag.sh
      cat > $DATA/diag.sh << EOFdiag
#!/bin/sh
lrun_subdirs=\$1
binary_diag=\$2
type=\$3
loop=\$4
string=\$5
CDATE=\$6
DIAG_COMPRESS=\$7
DIAG_SUFFIX=\$8
if [ \$lrun_subdirs = ".true." ]; then
   prefix=" dir.*/"
else
   prefix="pe*"
fi
file=diag_\${type}_\${string}.\${CDATE}\${DIAG_SUFFIX}
if [ \$binary_diag = ".true." ]; then
   cat \${prefix}\${type}_\${loop}* > \$file
else
   $catexec -o \$file \${prefix}\${type}_\${loop}*
fi
if [ \$DIAG_COMPRESS = "YES" ]; then
   $COMPRESS \$file
fi
EOFdiag
      chmod 755 $DATA/diag.sh
   fi

   # Collect diagnostic files as a function of loop and type.
   # Loop over first and last outer loops to generate innovation
   # diagnostic files for indicated observation types (groups)
   #
   # NOTE:  Since we set miter=2 in GSI namelist SETUP, outer
   #        loop 03 will contain innovations with respect to
   #        the analysis.  Creation of o-a innovation files
   #        is triggered by write_diag(3)=.true.  The setting
   #        write_diag(1)=.true. turns on creation of o-g
   #        innovation files.

   loops="01 02 03"
   for loop in $loops; do
      case $loop in
         01) string=ges;;
         03) string=anl;;
          *) string=$loop;;
      esac
      echo $(date) START loop $string >&2
      n=-1
      while [ $((n+=1)) -le $ntype ] ;do
         for type in $(echo ${diagtype[n]}); do
            count=$(ls ${prefix}${type}_${loop}* | wc -l)
            if [ $count -gt 1 ]; then
               if [ $USE_CFP = "YES" ]; then
                  echo "$DATA/diag.sh $lrun_subdirs $binary_diag $type $loop $string $CDATE $DIAG_COMPRESS $DIAG_SUFFIX" | tee -a $DATA/mp_diag.sh
               else
                  cat ${prefix}${type}_${loop}* > diag_${type}_${string}.${CDATE}${DIAG_SUFFIX}
               fi
               echo "diag_${type}_${string}.${CDATE}*" >> ${diaglist[n]}
               numfile[n]=$(expr ${numfile[n]} + 1)
	    elif [ $count -eq 1 ]; then
		cat ${prefix}${type}_${loop}* > diag_${type}_${string}.${CDATE}${DIAG_SUFFIX}
		echo "diag_${type}_${string}.${CDATE}*" >> ${diaglist[n]}
		numfile[n]=$(expr ${numfile[n]} + 1)
            fi
         done
      done
      echo $(date) END loop $string >&2
   done

   # We should already be in $DATA, but extra cd to be sure.
   cd $DIAG_DIR

   # If requested, compress diagnostic files
   if [ $DIAG_COMPRESS = "YES" -a $USE_CFP = "NO" ]; then
      echo $(date) START $COMPRESS diagnostic files >&2
      for file in $(ls diag_*${CDATE}${DIAG_SUFFIX}); do
         $COMPRESS $file
      done
      echo $(date) END $COMPRESS diagnostic files >&2
   fi

   if [ $USE_CFP = "YES" ] ; then
      chmod 755 $DATA/mp_diag.sh
      ncmd=$(cat $DATA/mp_diag.sh | wc -l)
      if [ $ncmd -gt 0 ]; then
         ncmd_max=$((ncmd < npe_node_max ? ncmd : npe_node_max))
         APRUNCFP_DIAG=$(eval echo $APRUNCFP)
         $APRUNCFP_DIAG $DATA/mp_diag.sh
      fi
   fi

   # If requested, create diagnostic file tarballs
   if [ $DIAG_TARBALL = "YES" ]; then
      echo $(date) START tar diagnostic files >&2
      n=-1
      while [ $((n+=1)) -le $ntype ] ;do
         TAROPTS="-uvf"
         if [ ! -s ${diagfile[n]} ]; then
            TAROPTS="-cvf"
         fi
         if [ ${numfile[n]} -gt 0 ]; then
            tar $TAROPTS ${diagfile[n]} $(cat ${diaglist[n]})
         fi
      done

      # Restrict CNVSTAT
      chmod 750 $CNVSTAT
      ${CHGRP_CMD} $CNVSTAT

      # Restrict RADSTAT
      chmod 750 $RADSTAT
      ${CHGRP_CMD} $RADSTAT

      echo $(date) END tar diagnostic files >&2
   fi

fi # End diagnostic file generation block - if [ $GENDIAG = "YES" ]

echo "after GENDIAG= $GENDIAG at `date`"

# If requested, clean up $DATA
if [[ "$CLEAN" = "YES" ]];then
   if [[ $rc -eq 0 ]];then
      rm -rf $DATA
      cd $DATA
      cd ../
      rmdir $DATA
   fi
fi
date

exit
