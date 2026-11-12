/*
 * Matter data model + stack glue for the H2 soil sensor.
 * Uses esp-matter (legacy data model API) with the Matter 1.5 Soil Sensor device type.
 */
#include "app_matter.h"

#include <cmath>
#include <cstdlib>
#include <cstring>

#include <esp_log.h>
#include <esp_matter.h>
#include <esp_matter_ota.h>
#include <esp_openthread.h>
#include <esp_openthread_lock.h>
#include <openthread/platform/radio.h>

#include <app/clusters/power-source-server/power-source-server.h>
#include <app/icd/server/ICDNotifier.h>
#include <app/server/CommissioningWindowManager.h>
#include <app/server/Server.h>
#include <clusters/relative_humidity_measurement/integration.h>
#include <clusters/soil_measurement/integration.h>
#include <clusters/temperature_measurement/integration.h>
#include <data_model_provider/esp_matter_data_model_provider.h>

#include "app_openthread_config.h"
#include "battery.h"
#include "status_led.h"

static const char *TAG = "app_matter";

/* log (instead of silently dropping) CHIP_ERROR results */
#define LOG_ON_CHIP_ERR(expr)                                                                          \
    do {                                                                                               \
        CHIP_ERROR _e = (expr);                                                                        \
        if (_e != CHIP_NO_ERROR) {                                                                     \
            ESP_LOGW(TAG, "%s: %" CHIP_ERROR_FORMAT, #expr, _e.Format());                              \
        }                                                                                              \
    } while (0)

using namespace esp_matter;
using namespace chip::app::Clusters;
using chip::app::DataModel::Nullable;

static constexpr uint16_t kInvalidEp = 0xFFFF;
static uint16_t s_ep_soil = kInvalidEp;
static uint16_t s_ep_soil_rh = kInvalidEp;
static constexpr uint16_t kEpRoot = 0;

/* Soil Measurement limits: 0..100 %, one accuracy range (+/-5 % absolute, after calibration).
 * The cluster keeps a reference to the ranges list -> static storage. */
static Globals::Structs::MeasurementAccuracyRangeStruct::Type s_soil_ranges[1];

/* ------------------------------------------------------------------ callbacks */
static void app_event_cb(const ChipDeviceEvent *event, intptr_t arg)
{
    switch (event->Type) {
    case chip::DeviceLayer::DeviceEventType::kCommissioningComplete:
        ESP_LOGI(TAG, "Commissioning complete");
        status_led_set(LED_CAL_DRY);   /* 2 blinks = joined */
        break;
    case chip::DeviceLayer::DeviceEventType::kCommissioningWindowOpened:
        ESP_LOGI(TAG, "Commissioning window opened");
        status_led_set(LED_COMMISSIONING);
        break;
    case chip::DeviceLayer::DeviceEventType::kCommissioningWindowClosed:
        ESP_LOGI(TAG, "Commissioning window closed");
        status_led_set(LED_OFF);
        break;
    case chip::DeviceLayer::DeviceEventType::kFailSafeTimerExpired:
        ESP_LOGW(TAG, "Commissioning failed (fail-safe expired)");
        status_led_set(LED_ERROR);
        break;
    case chip::DeviceLayer::DeviceEventType::kFabricRemoved:
        ESP_LOGI(TAG, "Fabric removed");
        if (chip::Server::GetInstance().GetFabricTable().FabricCount() == 0) {
            app_matter_open_commissioning_window();
        }
        break;
    case chip::DeviceLayer::DeviceEventType::kThreadStateChange: {
        /* (re)apply the configured TX power once the Thread stack is up */
        static bool s_tx_set = false;
        if (!s_tx_set && esp_openthread_get_instance()) {
            if (esp_openthread_lock_acquire(pdMS_TO_TICKS(100))) {
                otError e = otPlatRadioSetTransmitPower(esp_openthread_get_instance(), CONFIG_THREAD_TX_POWER_DBM);
                esp_openthread_lock_release();
                ESP_LOGI(TAG, "802.15.4 TX power %d dBm (%d)", CONFIG_THREAD_TX_POWER_DBM, e);
                s_tx_set = (e == OT_ERROR_NONE);
            }
        }
        break;
    }
    case chip::DeviceLayer::DeviceEventType::kBLEDeinitialized:
        ESP_LOGI(TAG, "BLE deinitialized, memory reclaimed");
        break;
    default:
        break;
    }
}

static esp_err_t app_identification_cb(identification::callback_type_t type, uint16_t endpoint_id, uint8_t effect_id,
                                       uint8_t effect_variant, void *priv_data)
{
    ESP_LOGI(TAG, "Identify ep%u type %u effect %u", endpoint_id, type, effect_id);
    if (type == identification::callback_type_t::START) {
        status_led_set(LED_IDENTIFY);
    } else if (type == identification::callback_type_t::STOP) {
        status_led_set(LED_OFF);
    } else {   /* trigger effect: blink once / few times */
        status_led_set(LED_CAL_WET);
    }
    return ESP_OK;
}

static esp_err_t app_attribute_update_cb(attribute::callback_type_t type, uint16_t endpoint_id, uint32_t cluster_id,
                                         uint32_t attribute_id, esp_matter_attr_val_t *val, void *priv_data)
{
    return ESP_OK;   /* sensor: no writable application attributes */
}

/* ------------------------------------------------------------------ data model */
static void add_power_source(node_t *node)
{
    endpoint_t *root = endpoint::get(node, kEpRoot);
    endpoint::power_source::config_t cfg;
    cfg.power_source.status = chip::to_underlying(PowerSource::PowerSourceStatusEnum::kActive);
    cfg.power_source.order = 0;
    strncpy(cfg.power_source.description, "CR123A", sizeof(cfg.power_source.description) - 1);
    cfg.power_source.feature_flags = cluster::power_source::feature::battery::get_id() |
                                     cluster::power_source::feature::replaceable::get_id();
    cfg.power_source.features.battery.bat_charge_level = chip::to_underlying(PowerSource::BatChargeLevelEnum::kOk);
    cfg.power_source.features.battery.bat_replacement_needed = false;
    cfg.power_source.features.battery.bat_replaceability =
        chip::to_underlying(PowerSource::BatReplaceabilityEnum::kUserReplaceable);
    strncpy(cfg.power_source.features.replaceable.bat_replacement_description, "CR123A 3V lithium (Li-MnO2)",
            sizeof(cfg.power_source.features.replaceable.bat_replacement_description) - 1);
    cfg.power_source.features.replaceable.bat_quantity = 1;
    /* Root Node rev.4 allows the Power Source utility device type on endpoint 0 */
    esp_err_t err = endpoint::power_source::add(root, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "power source: %s", esp_err_to_name(err));
        return;
    }
    cluster_t *ps = cluster::get(root, PowerSource::Id);
    cluster::power_source::attribute::create_bat_voltage(ps, nullable<uint32_t>(), nullable<uint32_t>(0),
                                                         nullable<uint32_t>(4500));
    cluster::power_source::attribute::create_bat_percent_remaining(ps, nullable<uint8_t>(), nullable<uint8_t>(0),
                                                                   nullable<uint8_t>(200));
}

esp_err_t app_matter_init(void)
{
    node::config_t node_config;
    node_t *node = node::create(&node_config, app_attribute_update_cb, app_identification_cb);
    if (!node) {
        ESP_LOGE(TAG, "node create failed");
        return ESP_FAIL;
    }

    /* EP1: Soil Sensor (Identify + Soil Measurement [+ Temperature Measurement]) */
    endpoint::soil_sensor::config_t soil_cfg;
    soil_cfg.identify.identify_type = chip::to_underlying(Identify::IdentifyTypeEnum::kVisibleIndicator);
    endpoint_t *ep = endpoint::soil_sensor::create(node, &soil_cfg, ENDPOINT_FLAG_NONE, nullptr);
    if (!ep) {
        ESP_LOGE(TAG, "soil sensor endpoint failed (esp-matter without Matter 1.5 support?)");
        return ESP_FAIL;
    }
    s_ep_soil = endpoint::get_id(ep);
    s_soil_ranges[0].rangeMin = 0;
    s_soil_ranges[0].rangeMax = 100;
    s_soil_ranges[0].fixedMax.SetValue(5);   /* +/-5 % after two-point calibration */
    Globals::Structs::MeasurementAccuracyStruct::Type limits;
    limits.measurementType = Globals::MeasurementTypeEnum::kSoilMoisture;
    limits.measured = true;
    limits.minMeasuredValue = 0;
    limits.maxMeasuredValue = 100;
    limits.accuracyRanges = chip::app::DataModel::List<const Globals::Structs::MeasurementAccuracyRangeStruct::Type>(
        s_soil_ranges, 1);
    SoilMeasurement::SetSoilMoistureLimits(s_ep_soil, limits);   /* must precede esp_matter::start() */

#if CONFIG_SOIL_ENABLE_RH_MIRROR
    /* EP2: soil moisture as relative humidity (compatibility) */
    endpoint::humidity_sensor::config_t mh;
    mh.relative_humidity_measurement.min_measured_value = nullable<uint16_t>(0);
    mh.relative_humidity_measurement.max_measured_value = nullable<uint16_t>(10000);
    endpoint_t *ep2 = endpoint::humidity_sensor::create(node, &mh, ENDPOINT_FLAG_NONE, nullptr);
    s_ep_soil_rh = ep2 ? endpoint::get_id(ep2) : kInvalidEp;
#endif


    add_power_source(node);

#if CHIP_DEVICE_CONFIG_ENABLE_THREAD
    esp_openthread_platform_config_t config = {
        .radio_config = ESP_OPENTHREAD_DEFAULT_RADIO_CONFIG(),
        .host_config = ESP_OPENTHREAD_DEFAULT_HOST_CONFIG(),
        .port_config = ESP_OPENTHREAD_DEFAULT_PORT_CONFIG(),
    };
    set_openthread_platform_config(&config);
#endif
    ESP_LOGI(TAG, "endpoints: soil=%u soilRH=%u", s_ep_soil, s_ep_soil_rh);
    return ESP_OK;
}

esp_err_t app_matter_start(void)
{
    esp_err_t err = esp_matter::start(app_event_cb);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_matter::start failed: %s", esp_err_to_name(err));
        return err;
    }
    /* Power Source EndpointList: the battery powers every endpoint of the node */
    static chip::EndpointId s_powered[3];
    size_t n = 0;
    s_powered[n++] = kEpRoot;
    for (uint16_t e : {s_ep_soil, s_ep_soil_rh}) {
        if (e != kInvalidEp) {
            s_powered[n++] = e;
        }
    }
    {
        lock::ScopedChipStackLock lock(portMAX_DELAY);
        LOG_ON_CHIP_ERR(PowerSourceServer::Instance().SetEndpointList(kEpRoot, chip::Span<chip::EndpointId>(s_powered, n)));
    }
    return ESP_OK;
}

/* ------------------------------------------------------------------ publishing */
typedef struct {
    bool valid;
    int32_t value;
    int64_t t_us;
} last_t;

static last_t s_last_soil, s_last_vbat;

/** Threshold / max-interval gate. Returns 0 = skip, 1 = value changed, 2 = heartbeat (unchanged). */
static int gate(last_t &l, int32_t v, int32_t delta, int64_t now, bool force)
{
    const int64_t max_us = (int64_t)CONFIG_SOIL_MAX_REPORT_INTERVAL_S * 1000000LL;
    if (force || !l.valid || std::abs(v - l.value) >= delta) {
        int r = (l.valid && v == l.value) ? 2 : 1;
        l = {true, v, now};
        return r;
    }
    if (now - l.t_us >= max_us) {
        int r = (v == l.value) ? 2 : 1;
        l = {true, v, now};
        return r;
    }
    return 0;
}

static void heartbeat(uint16_t ep, uint32_t cluster, uint32_t attr)
{
    /* value unchanged but the maximum interval elapsed: mark dirty so subscribers get a report */
    esp_matter::data_model::provider::get_instance().ReportAttributeChanged(
        chip::app::AttributePathParams(ep, cluster, attr));
}

void app_matter_publish(const sensor_readings_t *r, bool force)
{
    const int64_t now = esp_timer_get_time();
    lock::ScopedChipStackLock lock(portMAX_DELAY);

    if (r->soil_valid) {
        int32_t pct = (int32_t)lroundf(r->soil_pct);
        int g = gate(s_last_soil, pct, CONFIG_SOIL_REPORT_DELTA_PCT, now, force);
        if (g == 1) {
            LOG_ON_CHIP_ERR(SoilMeasurement::SetSoilMoistureMeasuredValue(s_ep_soil, Nullable<uint8_t>((uint8_t)pct)));
            if (s_ep_soil_rh != kInvalidEp) {
                LOG_ON_CHIP_ERR(RelativeHumidityMeasurement::SetMeasuredValue(s_ep_soil_rh, Nullable<uint16_t>((uint16_t)(pct * 100))));
            }
        } else if (g == 2) {
            heartbeat(s_ep_soil, SoilMeasurement::Id, SoilMeasurement::Attributes::SoilMoistureMeasuredValue::Id);
            if (s_ep_soil_rh != kInvalidEp) {
                heartbeat(s_ep_soil_rh, RelativeHumidityMeasurement::Id,
                          RelativeHumidityMeasurement::Attributes::MeasuredValue::Id);
            }
        }
    }
    if (r->vbat_valid) {
        int g = gate(s_last_vbat, r->vbat_mv, CONFIG_VBAT_REPORT_DELTA_MV, now, force);
        if (g == 1) {
            esp_matter_attr_val_t v = esp_matter_nullable_uint32(nullable<uint32_t>((uint32_t)r->vbat_mv));
            attribute::update(kEpRoot, PowerSource::Id, PowerSource::Attributes::BatVoltage::Id, &v);
            /* BatPercentRemaining is in half-percent units (0..200) */
            v = esp_matter_nullable_uint8(nullable<uint8_t>((uint8_t)(r->bat_pct * 2)));
            attribute::update(kEpRoot, PowerSource::Id, PowerSource::Attributes::BatPercentRemaining::Id, &v);
            v = esp_matter_enum8(battery_charge_level(r->bat_pct));
            attribute::update(kEpRoot, PowerSource::Id, PowerSource::Attributes::BatChargeLevel::Id, &v);
            v = esp_matter_bool(battery_replacement_needed(r->bat_pct));
            attribute::update(kEpRoot, PowerSource::Id, PowerSource::Attributes::BatReplacementNeeded::Id, &v);
        }
    }
}

/* ------------------------------------------------------------------ helpers */
bool app_matter_is_commissioned(void)
{
    lock::ScopedChipStackLock lock(portMAX_DELAY);
    return chip::Server::GetInstance().GetFabricTable().FabricCount() > 0;
}

void app_matter_open_commissioning_window(void)
{
    LOG_ON_CHIP_ERR(chip::DeviceLayer::PlatformMgr().ScheduleWork([](intptr_t) {
        auto &mgr = chip::Server::GetInstance().GetCommissioningWindowManager();
        if (mgr.IsCommissioningWindowOpen()) {
            return;
        }
        /* BLE + DNS-SD advertisement for 15 min (BLE is only used for commissioning) */
        CHIP_ERROR err = mgr.OpenBasicCommissioningWindow(chip::System::Clock::Seconds16(900),
                                                          chip::CommissioningWindowAdvertisement::kAllSupported);
        if (err != CHIP_NO_ERROR) {
            ESP_LOGE(TAG, "open commissioning window: %" CHIP_ERROR_FORMAT, err.Format());
        }
    }));
}

void app_matter_user_active_trigger(void)
{
    /* ICD: switch to Active Mode (fast polling) for ActiveModeThreshold so a controller can reach us */
    LOG_ON_CHIP_ERR(chip::DeviceLayer::PlatformMgr().ScheduleWork(
        [](intptr_t) { chip::app::ICDNotifier::GetInstance().NotifyNetworkActivityNotification(); }));
}

void app_matter_factory_reset(void)
{
    esp_matter::factory_reset();   /* erases Matter/Thread NVS and reboots */
}
