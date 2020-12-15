
# Latte Compiler

This is a project I made for compilers course at Warsaw University.

It still has some minor bugs and misses some major features (like support for many architectures, arrays), but is nonetheless an interesting and educational project - especially if one wants to know how compilers / x86 arch work. Besides that it probably doesn't have any real use.

## Example programs

Example programs can be found in `tests` subdirectory. Each program has `.lat` extentsion, `.expected` extension is for file which contains expected output should the compiled program be run.

## Dependencies

On 32bit linuxes only requirements are `Python3`, `virtualenv`, `gcc`, `java` and `nasm` (as the compiler uses Intel's assembly). Cross compiling on 64bit machines should be possible with `gcc-multilib` installed.

## Building and running

If the requirements are fullfilled simple `make` should be enough.
To test the compiler against example programs one can run `make test` (possibly changing `MACHINE` variable in `run_tests.sh` as I used `qemu-i386` on a different architecture).

To compile a Latte program simply run

```bash
./latc_x86 <example_program>
```

Finally, `make clean` will delete all generated files.
