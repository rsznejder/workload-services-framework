#!/bin/bash -e

if [ -r "$TEST_CONFIG" ]; then
    TESTCASE_CUSTOMIZED=""
    _insection=0
    _prefix=undef
    while IFS= read _line; do
        _prefix1="$(echo "$_line" | sed 's/[^ ].*$//')"
        [[ "$_line" = "#"* ]] && continue
        [[ "$_line" != *:* ]] && continue
        _k="$(echo "$_line" | cut -f1 -d: | sed -e 's|^ *||' -e 's| *$||' | tr -d "\"'")"
        _v="$(echo "$_line" | cut -f2- -d: | sed -e 's|^ *||' -e 's| *$||' | tr -d "\"'")"
        [ $_prefix = undef ] && _prefix=${#_prefix1}
        if [ ${#_prefix1} -eq $_prefix ]; then
            case "$TESTCASE" in
            $_k)
                _insection=1;;
            *)
                _insection=0;;
            esac
        elif [ $_insection -gt 0 ] && [ ${#_prefix1} -gt $_prefix ]; then
            eval "_tmp2=\"\${$_k}\""
            if [ "$_v" != "$_tmp2" ]; then
                eval "export $_k=\"$_v\""
                echo "OVERWRITE: $_k=$_v"
                TESTCASE_CUSTOMIZED="_customized"
            fi
        fi
    done < <(cat "$TEST_CONFIG"; echo)
    # save test config
    cp -f "$TEST_CONFIG" "${LOGSDIRH:-$(pwd)}/test-config.yaml" > /dev/null 2>&1 || echo -n ""
fi
