#!/bin/bash

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TEST_DIR=$HERE/tests
success=true

MACHINE="qemu-i386" 
# ^ change this to empty string when running elf 32 natively


for latte_file in $TEST_DIR/*.lat; do 
    fname=$(basename $latte_file .lat)
    input_file=$TEST_DIR/$fname.input
    expected_file=$TEST_DIR/$fname.expected

    echo "Compiling $fname.lat"
    compile_output=$($HERE/latc_x86 $latte_file)

    if [ $? == 0 ] 
    then
        out_file=$TEST_DIR/$fname.out

        if [ -f $input_file ] 
        then
            output=$(cat $input_file | $MACHINE $out_file)
        else
            output=$($MACHINE $out_file)
        fi 

        if [ -f $expect_file ] 
        then
            expected_output=$(cat $expected_file)
            if [ "$output" = "$expected_output" ]; then
                echo -e "\e[0;92mTest $fname.lat passed!\e[0m"
            else
                echo -e "\e[0;31mBad output for $fname.lat!\e[0m"
                success=false

                echo "$expected_output" >$TEST_DIR/expected.tmp
                echo "$output" >$TEST_DIR/output.tmp
                diff $TEST_DIR/expected.tmp $TEST_DIR/output.tmp
                rm $TEST_DIR/{expected,output}.tmp
            fi
        fi
    else
        echo -e "\e[0;31mFailed to compile $fname.lat!\e[0m"
        echo "Copiler output: $compile_output"
        success=false
    fi

    rm -rf $out_file $TEST_DIR/$fname.o $TEST_DIR/$fname.asm
done

([[ "$success" = true ]] && echo -e "\e[0;92mAll tests passed!\e[0m" ) || echo -e "\e[0;31mSome tests failed!\e[0m"
