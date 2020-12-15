
1. Instalacja

Kompilator napisany jest w Pythonie 3 (3.8). Poza standardowymi bibliotekami wykorzystuje generator parserów antlr4.
Projekt powinien budować się samodzielnie poleceniem `make`. Potrzebnym plikiem do jego uruchomienia jest jar
antlera znajdujący się w katalogu lib (do wygenerowania parsera), oraz zainstalowany virtualenv i połączenie z internetem 
(polecenie make instaluje w virtualenvie runtime antlera).

2. Środowisko

Kompilator kompiluje do 32-bitowego x86 (wersja Intela), wygeneroany kod działa na Linuxie. W 64-bitowych systemach może być potrzebna instalacja gcc-multilib (apt install gcc-multilib). Do generowania kodu maszynowego z assemblera używany jest nasm, więc potrzebne może okazać się polecenie: apt install nasm.

3. Rozszerzenia
    * struktury
    * obiekty
    * metody wirtualne
    * proste optymalizacje

4. Proste optymalizacje, które zastosowano, to:
    * eliminacja stałych wyrażeń (które nie zawierają zmiennych ani calli)
    * eliminacja nieosiągalnego kodu (np. while ze stałym fałszywym warunkiem)
    * nie używanie stosu (push / pop) do obliczania wyrażeń, ograniczenie liczby zmiennych
    * peephole optimization, która optymalizuje takie fragmenty jak [notacja Intel]:

        mov a, b         mov a, b      jmp l
        mov b, a         mov a, c      l:        itp.

5. Struktura
    Kod źródłowy znajduje się w katalogu ./src. W ./src/antlr4gen, po wykonaniu make, znajduje się kod wygenerowany przez antlera.
    Entrypoint kompilatora znajduje się w latc.py. W latt_state.py znajdują się klasy odpowiedzialne za budowanie / trzymanie stanu
    związanego z programem (informacje o klasach, sygnatury metod itd.). W plikach error_checker.py / errors.py są jest kod odpowiedzialny za
    sprawdzanie poprawności programu. Pliki string_finder.py, locals_counter.py, expression_evaluator.py zawierają kod modyfikujący wierzchołki drzewa, przydatny później. W tree_optimizer.py jest kod obliczający wyrażenia stałe i eliminjący nieosiągalny kod. Backend znajduje się w plikach
    assembly_generator.py, assembly_writer.py, variable_allocator.py i peephole_optimizer.py; w pierwszym jest główny kod kompilatora.

6. Uwagi:
    * Optymalizacja stałych wyrażeń następuje po sprawdzeniu typów, więc np. kod

        int main(){
            if (1 == 2){
                return "cokolwiek";
            }
            return 0;
        }

      zostanie uznany za błędny. Gdyby wewnątrz if zwracany był int, to cały if zostałby usunięty.
    * Podobnie jak w C++, gdy do wywołania, które znajduje się wewnątrz metody, pasuje zarówna funkcja jak i metoda danej klasy, to wywołana
    zostanie metoda tej klasy. Np. poniższy kod wypisze napis "metoda":

        class A{
            void f(){printString("metoda");}
            void g(){f();}
        }
        
        void f(){printString("funkcja");}

        int main(){
            A a = new A;
            a.g();
            return 0;
        }
    * Optymalizacje można włączć / wyłączać flagami --peephole oraz --const_expr. Więcej: ./latc_x86 --help.
