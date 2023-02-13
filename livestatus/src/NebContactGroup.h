// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContactGroup_h
#define NebContactGroup_h

#include <string>

#include "livestatus/Interface.h"
#include "nagios.h"

class NebContactGroup : public IContactGroup {
public:
    // Older Nagios headers are not const-correct... :-P
    explicit NebContactGroup(const std::string &name)
        : contact_group_{
              ::find_contactgroup(const_cast<char *>(name.c_str()))} {}
    explicit NebContactGroup(const contactgroup &contact_group)
        : contact_group_{&contact_group} {}
    [[nodiscard]] const void *handle() const override { return contact_group_; }
    // Older Nagios headers are not const-correct... :-P
    [[nodiscard]] bool isMember(const IContact &contact) const override {
        return ::is_contact_member_of_contactgroup(
                   const_cast<contactgroup *>(contact_group_),
                   const_cast<::contact *>(
                       static_cast<const ::contact *>(contact.handle()))) != 0;
    }
    [[nodiscard]] std::string name() const override {
        return contact_group_->group_name == nullptr
                   ? ""
                   : contact_group_->group_name;
    }
    [[nodiscard]] std::string alias() const override {
        return contact_group_->alias == nullptr ? "" : contact_group_->alias;
    }
    [[nodiscard]] std::vector<std::string> contactNames() const override {
        std::vector<std::string> names;
        for (const auto *cm = contact_group_->members; cm != nullptr;
             cm = cm->next) {
            names.emplace_back(cm->contact_ptr->name);
        }
        return names;
    }

private:
    const contactgroup *contact_group_;
};

#endif  // NebContactGroup_h
