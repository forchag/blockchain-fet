#include "unity.h"

#include "crt_encode.h"

static void assert_round_trip_from_pair(uint32_t reading, uint8_t a,
                                        uint8_t b) {
  crt_residue_t residues[CRT_RESIDUE_COUNT];
  TEST_ASSERT_EQUAL(ESP_OK, crt_encode(reading, residues));

  crt_residue_t pair[2] = {residues[a], residues[b]};
  uint32_t decoded = UINT32_MAX;
  TEST_ASSERT_EQUAL(ESP_OK, crt_decode(pair, &decoded));
  TEST_ASSERT_EQUAL_UINT32(reading, decoded);
}

TEST_CASE("CRT encodes residues for all moduli", "[crt]") {
  crt_residue_t residues[CRT_RESIDUE_COUNT];
  TEST_ASSERT_EQUAL(ESP_OK, crt_encode(123456, residues));
  TEST_ASSERT_EQUAL_UINT8(0, residues[0].index);
  TEST_ASSERT_EQUAL_UINT8(123456 % CRT_MODULUS_0, residues[0].value);
  TEST_ASSERT_EQUAL_UINT8(1, residues[1].index);
  TEST_ASSERT_EQUAL_UINT8(123456 % CRT_MODULUS_1, residues[1].value);
  TEST_ASSERT_EQUAL_UINT8(2, residues[2].index);
  TEST_ASSERT_EQUAL_UINT8(123456 % CRT_MODULUS_2, residues[2].value);
}

TEST_CASE("CRT rejects values outside representable range", "[crt]") {
  crt_residue_t residues[CRT_RESIDUE_COUNT];
  TEST_ASSERT_EQUAL(ESP_ERR_INVALID_SIZE, crt_encode(CRT_MAX_VALUE, residues));
}

TEST_CASE("CRT decodes zero from any two residues", "[crt]") {
  assert_round_trip_from_pair(0, 0, 1);
  assert_round_trip_from_pair(0, 0, 2);
  assert_round_trip_from_pair(0, 1, 2);
}

TEST_CASE("CRT decodes mid-range reading from any two residues", "[crt]") {
  assert_round_trip_from_pair(500000, 0, 1);
  assert_round_trip_from_pair(500000, 0, 2);
  assert_round_trip_from_pair(500000, 1, 2);
}

TEST_CASE("CRT decodes highest supported reading from any two residues",
          "[crt]") {
  assert_round_trip_from_pair(CRT_MAX_VALUE - 1, 0, 1);
  assert_round_trip_from_pair(CRT_MAX_VALUE - 1, 0, 2);
  assert_round_trip_from_pair(CRT_MAX_VALUE - 1, 1, 2);
}

TEST_CASE("CRT rejects invalid decode pairs", "[crt]") {
  uint32_t decoded = 0;
  crt_residue_t duplicate[2] = {{.index = 0, .value = 1},
                                {.index = 0, .value = 2}};
  TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crt_decode(duplicate, &decoded));

  crt_residue_t invalid_index[2] = {{.index = 3, .value = 1},
                                    {.index = 1, .value = 2}};
  TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crt_decode(invalid_index, &decoded));

  crt_residue_t invalid_value[2] = {{.index = 0, .value = CRT_MODULUS_0},
                                    {.index = 1, .value = 2}};
  TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crt_decode(invalid_value, &decoded));
}
