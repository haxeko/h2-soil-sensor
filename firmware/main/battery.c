#include "battery.h"

/* loaded voltage (mV) -> remaining capacity (%), CR123A at a few-mA load, 20 degC */
static const struct {
    int mv;
    uint8_t pct;
} k_curve[] = {
    {3050, 100}, {2980, 90}, {2930, 75}, {2890, 60}, {2850, 45},
    {2800, 30},  {2740, 20}, {2650, 10}, {2500, 5},  {2300, 2}, {2000, 0},
};

uint8_t battery_percent(int mv)
{
    const int n = sizeof(k_curve) / sizeof(k_curve[0]);
    if (mv >= k_curve[0].mv) {
        return 100;
    }
    if (mv <= k_curve[n - 1].mv) {
        return 0;
    }
    for (int i = 1; i < n; i++) {
        if (mv >= k_curve[i].mv) {
            int dv = k_curve[i - 1].mv - k_curve[i].mv;
            int dp = k_curve[i - 1].pct - k_curve[i].pct;
            return (uint8_t)(k_curve[i].pct + (mv - k_curve[i].mv) * dp / dv);
        }
    }
    return 0;
}

uint8_t battery_charge_level(uint8_t pct)
{
    if (pct <= 5) {
        return 2;   /* Critical */
    }
    if (pct <= 20) {
        return 1;   /* Warning */
    }
    return 0;       /* OK */
}

bool battery_replacement_needed(uint8_t pct)
{
    return pct <= 10;
}
