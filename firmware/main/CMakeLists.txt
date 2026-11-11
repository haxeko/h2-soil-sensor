# "main" keeps the implicit dependency on every component of the build (esp_matter, chip, button, ...)
idf_component_register(SRC_DIRS          "."
                       PRIV_INCLUDE_DIRS  "." "${ESP_MATTER_PATH}/examples/common/utils")

target_compile_options(${COMPONENT_LIB} PRIVATE "-DCHIP_HAVE_CONFIG_H")
