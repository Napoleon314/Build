INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("cares" "ares.h" "" "")
ELSE()
  VE_FIND_LIBRARY("cares" "ares.h" "" "CARES_STATICLIB")
ENDIF()
