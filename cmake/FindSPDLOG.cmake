INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("spdlog" "spdlog/spdlog.h" "" "SPDLOG_SHARED_LIB;FMT_SHARED")
ELSE()
  VE_FIND_LIBRARY("spdlog" "spdlog/spdlog.h" "" "")
ENDIF()
