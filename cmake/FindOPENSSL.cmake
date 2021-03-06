IF(NOT OPENSSL_FOUND)
  SET(OPENSSL_FOUND true)
  IF(BUILD_IS_DEV_PLATFORM)
    IF(BUILD_LIB MATCHES "SHARED")
      SET(_PATH ${BUILD_PLATFORM_NAME}_${BUILD_ARCH_NAME}_shared)
    ELSE()
      SET(_PATH ${BUILD_PLATFORM_NAME}_${BUILD_ARCH_NAME})
    ENDIF()
  ELSEIF(BUILD_PLATFORM_IOS)
    SET(_PATH ${BUILD_PLATFORM_FOLDER_NAME})
  ELSE()
    IF(BUILD_ARCH_NAME STREQUAL "arm32")
      SET(_PATH ${BUILD_PLATFORM_FOLDER_NAME}_arm)
    ELSE()
      SET(_PATH ${BUILD_PLATFORM_FOLDER_NAME}_${BUILD_ARCH_NAME})
    ENDIF()
  ENDIF()
  IF(BUILD_PLATFORM_WINDOWS)
    SET(LIB_EXT lib)
  ELSEIF(BUILD_LIB STREQUAL "SHARED" AND BUILD_PLATFORM_DARWIN)
    SET(LIB_EXT a)
  ELSEIF(BUILD_LIB STREQUAL "SHARED")
    SET(LIB_EXT so)
  ELSE()
    SET(LIB_EXT a)
  ENDIF()
  IF(DEFINED VENUS3D_ROOT)
    SET(OPENSSL_INCLUDE_DIR ${VENUS3D_ROOT}/Dependencies/openssl/${_PATH}/include)
    IF(NOT EXISTS ${OPENSSL_INCLUDE_DIR}/openssl/ssl.h)
      SET(OPENSSL_FOUND false)
      UNSET(OPENSSL_INCLUDE_DIR)
    ENDIF()
    SET(OPENSSL_SSL_LIBRARY ${VENUS3D_ROOT}/Dependencies/openssl/${_PATH}/lib/libssl.${LIB_EXT})
    IF(NOT EXISTS ${OPENSSL_SSL_LIBRARY})
      SET(OPENSSL_FOUND false)
      UNSET(OPENSSL_SSL_LIBRARY)
    ENDIF()
    SET(OPENSSL_CRYPTO_LIBRARY ${VENUS3D_ROOT}/Dependencies/openssl/${_PATH}/lib/libcrypto.${LIB_EXT})
    IF(NOT EXISTS ${OPENSSL_CRYPTO_LIBRARY})
      SET(OPENSSL_FOUND false)
      UNSET(OPENSSL_CRYPTO_LIBRARY)
    ENDIF()
    SET(OPENSSL_LIBRARY ${OPENSSL_SSL_LIBRARY} ${OPENSSL_CRYPTO_LIBRARY})
    MARK_AS_ADVANCED(OPENSSL_LIBRARY)
    IF(OPENSSL_FOUND)
      SET(OPENSSL_USER_DEFINITIONS "USE_OPENSSL")
      GET_FILENAME_COMPONENT(_LIB_DIR ${OPENSSL_SSL_LIBRARY} DIRECTORY)
      MESSAGE(STATUS "[openssl] found in \"${_LIB_DIR}\"")
    ELSE()
      MESSAGE(FATAL_ERROR "[openssl] not found")
    ENDIF()
  ENDIF()
ENDIF()
