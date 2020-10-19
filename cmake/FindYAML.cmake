INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("yaml" "yaml.h" "" "")
ELSE()
  VE_FIND_LIBRARY("yaml" "yaml.h" "" "YAML_DECLARE_STATIC")
ENDIF()
