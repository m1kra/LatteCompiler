lib=./lib
src=./src
venv=./venv

antlr4jar=$(lib)/antlr4_complete.jar
antlr4gen=$(src)/antlr4gen
grammar=Latte.g4

runtimec=$(src)/runtime.c
runtimeo=$(lib)/runtime.o

.PHONY: test clean

all: venv $(antlr4gen) $(runtimeo)

venv:
	virtualenv -p python3 $(venv)
	$(venv)/bin/pip install antlr4-python3-runtime

$(antlr4gen): $(grammar)
	mkdir -p $(antlr4gen)
	java -jar $(antlr4jar) -Dlanguage=Python3 -visitor -no-listener -o $(antlr4gen) $(grammar)

$(runtimeo): $(runtimec)
	gcc -m32 -c $(runtimec) -o $(runtimeo)

test:
	./run_tests.sh

clean:
	rm -rf $(venv) $(antlr4gen) $(runtimeo)