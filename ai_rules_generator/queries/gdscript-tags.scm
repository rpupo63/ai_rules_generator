(function_definition
  name: (name) @name.definition.function) @definition.function

(class_name_statement
  (name) @name.definition.class) @definition.class

(signal_statement
  (name) @name.definition.signal) @definition.signal

(variable_statement
  (name) @name.definition.variable) @definition.variable

(call
  (identifier) @name.reference.call) @reference.call
