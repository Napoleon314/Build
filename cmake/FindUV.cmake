INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("uv" "uv.h" "" "USING_UV_SHARED=1")
ELSE()
  VE_FIND_LIBRARY("uv" "uv.h" "" "")
ENDIF()