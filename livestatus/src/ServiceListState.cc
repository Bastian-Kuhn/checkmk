// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceListState.h"

#include "livestatus/User.h"

#ifdef CMC
#include "CmcService.h"
#include "Service.h"
#include "State.h"
#else
#include "NebService.h"
#endif

int32_t ServiceListState::operator()(const value_type &svcs,
                                     const User &user) const {
    return getValueFromServices(user, _logictype, svcs);
}

// static
int32_t ServiceListState::getValueFromServices(const User &user, Type logictype,
                                               const value_type &svcs) {
    int32_t result = 0;
#ifdef CMC
    for (const auto &svc : svcs) {
        if (user.is_authorized_for_service(CmcService{*svc})) {
            const auto *state = svc->state();
            update(logictype, static_cast<ServiceState>(state->current_state_),
                   static_cast<ServiceState>(state->hard_state_.last_),
                   state->has_been_checked_, svc->handled(), result);
        }
    }
#else
    for (servicesmember *mem = svcs; mem != nullptr; mem = mem->next) {
        service *svc = mem->service_ptr;
        if (user.is_authorized_for_service(NebService{*svc})) {
            update(logictype, static_cast<ServiceState>(svc->current_state),
                   static_cast<ServiceState>(svc->last_hard_state),
                   svc->has_been_checked != 0,
                   svc->problem_has_been_acknowledged != 0 ||
                       svc->scheduled_downtime_depth > 0,
                   result);
        }
    }
#endif
    return result;
}

// static
void ServiceListState::update(Type logictype, ServiceState current_state,
                              ServiceState last_hard_state,
                              bool has_been_checked, bool handled,
                              int32_t &result) {
    switch (logictype) {
        case Type::num:
            result++;
            break;
        case Type::num_pending:
            if (!has_been_checked) {
                result++;
            }
            break;
        case Type::num_handled_problems:
            if (has_been_checked && current_state != ServiceState::ok &&
                handled) {
                result++;
            }
            break;
        case Type::num_unhandled_problems:
            if (has_been_checked && current_state != ServiceState::ok &&
                !handled) {
                result++;
            }
            break;
        case Type::num_ok:
            if (has_been_checked && current_state == ServiceState::ok) {
                result++;
            }
            break;
        case Type::num_warn:
            if (has_been_checked && current_state == ServiceState::warning) {
                result++;
            }
            break;
        case Type::num_crit:
            if (has_been_checked && current_state == ServiceState::critical) {
                result++;
            }
            break;
        case Type::num_unknown:
            if (has_been_checked && current_state == ServiceState::unknown) {
                result++;
            }
            break;
        case Type::worst_state:
            if (worse(current_state, static_cast<ServiceState>(result))) {
                result = static_cast<int32_t>(current_state);
            }
            break;
        case Type::num_hard_ok:
            if (has_been_checked && last_hard_state == ServiceState::ok) {
                result++;
            }
            break;
        case Type::num_hard_warn:
            if (has_been_checked && last_hard_state == ServiceState::warning) {
                result++;
            }
            break;
        case Type::num_hard_crit:
            if (has_been_checked && last_hard_state == ServiceState::critical) {
                result++;
            }
            break;
        case Type::num_hard_unknown:
            if (has_been_checked && last_hard_state == ServiceState::unknown) {
                result++;
            }
            break;
        case Type::worst_hard_state:
            if (worse(last_hard_state, static_cast<ServiceState>(result))) {
                result = static_cast<int32_t>(last_hard_state);
            }
            break;
    }
}
