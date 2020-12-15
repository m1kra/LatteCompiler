grammar Latte;

program
    : topDef+
    ;

topDef
    : funDef                                               # TopFunDef
    | 'class' ID '{' fieldDef* funDef* '}'                 # BaseClassDef
    | 'class' ID 'extends' ID '{' fieldDef* funDef* '}'    # ExtClassDef
    ;

fieldDef
    : type_ ID ( ',' ID )* ';'
    ;

funDef
    : type_ ID '(' arg? ')' block
    ;

arg
    : type_ ID ( ',' type_ ID )*
    ;

block
    : '{' stmt* '}'
    ;

stmt
    : ';'                                  # Empty
    | block                                # BlockStmt
    | type_ item ( ',' item )* ';'         # Decl
    | ID '=' expr ';'                      # Ass
    | expr '.' ID '=' expr ';'             # AttrAss
    | expr '[' expr ']' '=' expr ';'       # ArrayAss
    | ID '++' ';'                          # Incr
    | ID '--' ';'                          # Decr
    | expr '.' ID '++' ';'                 # AttrIncr
    | expr '.' ID '--' ';'                 # AttrDecr
    | 'return' expr ';'                    # Ret
    | 'return' ';'                         # VRet
    | 'if' '(' expr ')' stmt               # Cond
    | 'if' '(' expr ')' stmt 'else' stmt   # CondElse
    | 'while' '(' expr ')' stmt            # While
    | 'for' '(' type_ ID ':' expr ')' stmt # ForEach
    | expr ';'                             # SExp
    ;


type_
    : 'int'         # Int
    | 'string'      # Str
    | 'boolean'     # Bool
    | 'void'        # Void
    | ID            # Class
    | type_ '[' ']' # Array
    ;

item
    : ID           # Def
    | ID '=' expr  # DefAss
    ;

expr
    : expr '.' ID '(' ( expr ( ',' expr )* )? ')' # EMthdCall
    | expr '.' ID                                 # EAttr
    | unOp expr                                   # EUnOp
    | expr mulOp expr                             # EMulOp
    | expr addOp expr                             # EAddOp
    | expr relOp expr                             # ERelOp
    | <assoc=right> expr '&&' expr                # EAnd
    | <assoc=right> expr '||' expr                # EOr
    | ID                                          # EId
    | INT                                         # EInt
    | 'true'                                      # ETrue
    | 'false'                                     # EFalse
    | 'new' type_                                 # ENewObj
    | ID '(' ( expr ( ',' expr )* )? ')'          # EFunCall
    | STR                                         # EStr
    | '(' type_ ')' 'null'                        # ECastNull
    | '(' expr ')'                                # EParen
    | expr '[' expr ']'                           # EArrAcc
    | 'new' type_ '[' expr ']'                    # ENewArr
    | 'self'                                      # ESelf
    ;

unOp
    : '-' # Minus
    | '!' # Neg
    ;

addOp
    : '+' # Add
    | '-' # Sub
    ;

mulOp
    : '*' # Mul
    | '/' # Div
    | '%' # Mod
    ;

relOp
    : '<'  # Lt
    | '<=' # Le
    | '>'  # Gt
    | '>=' # Ge
    | '==' # Eq
    | '!=' # Neq
    ;

COMMENT : ('#' ~[\r\n]* | '//' ~[\r\n]*) -> channel(HIDDEN);
MULTICOMMENT : '/*' .*? '*/' -> channel(HIDDEN);

fragment Letter  : Capital | Small ;
fragment Capital : [A-Z\u00C0-\u00D6\u00D8-\u00DE] ;
fragment Small   : [a-z\u00DF-\u00F6\u00F8-\u00FF] ;
fragment Digit : [0-9] ;

INT : Digit+ ;
fragment ID_First : Letter | '_';
ID : ID_First (ID_First | Digit)* ;

WS : (' ' | '\r' | '\t' | '\n')+ ->  skip;

STR
    :   '"' StringCharacters? '"'
    ;
fragment StringCharacters
    :   StringCharacter+
    ;
fragment
StringCharacter
    :   ~["\\]
    |   '\\' [tnr"\\]
    ;
