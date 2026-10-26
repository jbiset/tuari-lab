<?php

defined('CLI_SCRIPT') && CLI_SCRIPT || die('CLI only');

function lab_set_user(stdClass $user): void {


    $sessionuser = clone $user;
    unset($sessionuser->access, $sessionuser->enrol);
    \core\session\manager::set_user($sessionuser);
    reload_all_capabilities();
}
