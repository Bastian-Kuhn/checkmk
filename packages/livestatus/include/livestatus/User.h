// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef auth_h
#define auth_h

#include <functional>
#include <memory>
#include <string>

// Different versions of the system headers differ in their requirements. :-/
#include "livestatus/Interface.h"  // IWYU pragma: keep

enum class ServiceAuthorization {
    loose = 0,   // contacts for hosts see all services
    strict = 1,  // must be explicit contact of a service
};

enum class GroupAuthorization {
    loose = 0,   // sufficient to be contact for one member
    strict = 1,  // must be contact of all members

};

class User {
public:
    virtual ~User() = default;
    [[nodiscard]] virtual bool is_authorized_for_object(
        const IHost *hst, const IService *svc,
        bool authorized_if_no_host) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_host(
        const IHost &hst) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_service(
        const IService &svc) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_host_group(
        const IHostGroup &hg) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_service_group(
        const IServiceGroup &sg) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_event(
        const std::string &precedence, const std::string &contact_groups,
        const IHost *hst) const = 0;
};

class AuthUser : public User {
public:
    AuthUser(std::unique_ptr<IContact> auth_user,
             ServiceAuthorization service_auth, GroupAuthorization group_auth,
             std::function<std::unique_ptr<IContactGroup>(const std::string &)>
                 make_contact_group);

    [[nodiscard]] bool is_authorized_for_object(
        const IHost *hst, const IService *svc,
        bool authorized_if_no_host) const override;
    [[nodiscard]] bool is_authorized_for_host(const IHost &hst) const override;
    [[nodiscard]] bool is_authorized_for_service(
        const IService &svc) const override;
    [[nodiscard]] bool is_authorized_for_host_group(
        const IHostGroup &hg) const override;
    [[nodiscard]] bool is_authorized_for_service_group(
        const IServiceGroup &sg) const override;
    [[nodiscard]] bool is_authorized_for_event(
        const std::string &precedence, const std::string &contact_groups,
        const IHost *hst) const override;

private:
    std::unique_ptr<IContact> auth_user_;
    ServiceAuthorization service_auth_;
    GroupAuthorization group_auth_;
    std::function<std::unique_ptr<IContactGroup>(const std::string &)>
        make_contact_group_;
};

class NoAuthUser : public User {
public:
    [[nodiscard]] bool is_authorized_for_object(
        const IHost * /* hst */, const IService * /* svc */,
        bool /*authorized_if_no_host*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_host(
        const IHost & /*hst*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_service(
        const IService & /*svc*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_host_group(
        const IHostGroup & /*hg*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_service_group(
        const IServiceGroup & /*sg*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_event(
        const std::string & /*precedence*/,
        const std::string & /*contact_groups*/,
        const IHost * /*hst*/) const override {
        return true;
    }
};

class UnknownUser : public User {
public:
    [[nodiscard]] bool is_authorized_for_object(
        const IHost *hst, const IService * /* svc */,
        bool authorized_if_no_host) const override {
        return hst == nullptr && authorized_if_no_host;
    }
    [[nodiscard]] bool is_authorized_for_host(
        const IHost & /*hst*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_service(
        const IService & /*svc*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_host_group(
        const IHostGroup & /*hg*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_service_group(
        const IServiceGroup & /*sg*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_event(
        const std::string & /*precedence*/,
        const std::string & /*contact_groups*/,
        const IHost * /*hst*/) const override {
        return false;
    }
};

#endif  // auth_h
