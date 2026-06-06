idf_component_register(
    SRCS
        "main.c"
        "sensor.c"
        "signing.c"
        "cert_store.c"
        "lora_tx.c"
        "crt_encode.c"
    INCLUDE_DIRS "."
    REQUIRES nvs_flash esp_adc driver esp_timer esp_event esp_netif lwip wolfssl
)
