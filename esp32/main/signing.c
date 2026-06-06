#include "signing.h"

#include <stdbool.h>
#include <string.h>

#include <wolfssl/wolfcrypt/ed25519.h>
#include <wolfssl/wolfcrypt/sha256.h>

#include "cert_store.h"

static void wipe_key(uint8_t key[CERT_PRIVATE_KEY_LEN]) {
  explicit_bzero(key, CERT_PRIVATE_KEY_LEN);
}

esp_err_t sign_sensor_data(const uint8_t *payload, size_t payload_len,
                           uint8_t signature[SIGNATURE_LEN]) {
  if (payload == NULL || signature == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  uint8_t digest[SHA256_DIGEST_LEN];
  uint8_t private_key[CERT_PRIVATE_KEY_LEN];
  ed25519_key key;
  word32 sig_len = SIGNATURE_LEN;
  int wolf_err;

  esp_err_t err = private_key_read(private_key);
  if (err != ESP_OK) {
    wipe_key(private_key);
    return err;
  }

  wolf_err = wc_Sha256Hash(payload, (word32)payload_len, digest);
  if (wolf_err != 0) {
    wipe_key(private_key);
    explicit_bzero(digest, sizeof(digest));
    return ESP_FAIL;
  }

  wc_ed25519_init(&key);
  wolf_err =
      wc_ed25519_import_private_only(private_key, CERT_PRIVATE_KEY_LEN, &key);
  if (wolf_err == 0) {
    wolf_err =
        wc_ed25519_sign_msg(digest, sizeof(digest), signature, &sig_len, &key);
  }
  wc_ed25519_free(&key);

  wipe_key(private_key);
  explicit_bzero(digest, sizeof(digest));

  if (wolf_err != 0 || sig_len != SIGNATURE_LEN) {
    return ESP_FAIL;
  }
  return ESP_OK;
}

esp_err_t verify_gateway_signature(const uint8_t *payload, size_t payload_len,
                                   const uint8_t signature[SIGNATURE_LEN]) {
  if (payload == NULL || signature == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  uint8_t digest[SHA256_DIGEST_LEN];
  uint8_t gateway_pubkey[CERT_GATEWAY_PUBKEY_LEN];
  ed25519_key key;
  int verified = 0;

  esp_err_t err = cert_store_get_gateway_pubkey(gateway_pubkey);
  if (err != ESP_OK) {
    return err;
  }

  int wolf_err = wc_Sha256Hash(payload, (word32)payload_len, digest);
  if (wolf_err != 0) {
    explicit_bzero(digest, sizeof(digest));
    return ESP_FAIL;
  }

  wc_ed25519_init(&key);
  wolf_err =
      wc_ed25519_import_public(gateway_pubkey, CERT_GATEWAY_PUBKEY_LEN, &key);
  if (wolf_err == 0) {
    wolf_err = wc_ed25519_verify_msg(signature, SIGNATURE_LEN, digest,
                                     sizeof(digest), &verified, &key);
  }
  wc_ed25519_free(&key);
  explicit_bzero(digest, sizeof(digest));

  return (wolf_err == 0 && verified == 1) ? ESP_OK : ESP_ERR_INVALID_RESPONSE;
}
