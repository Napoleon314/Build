INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("zlib" "zlib.h" "" "ZLIB_DLL")
ELSE()
  VE_FIND_LIBRARY("zlib" "zlib.h" "" "")
ENDIF()
