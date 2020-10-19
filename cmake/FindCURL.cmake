INCLUDE(FindLibrary)

IF(BUILD_LIB MATCHES "SHARED")
  VE_FIND_LIBRARY("curl" "curl/curl.h" "zlib;cares" "")
ELSE()
  VE_FIND_LIBRARY("curl" "curl/curl.h" "zlib;cares" "CURL_STATICLIB")
ENDIF()
