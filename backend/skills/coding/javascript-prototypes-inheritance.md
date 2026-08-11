---
lang: javascript
keywords: prototype, inheritance, Object.create, constructor function, prototype chain, new keyword, hasOwnProperty, instanceof, class extends, prototype pollution
---

# Prototypes & inheritance

Every JS object has a hidden `[[Prototype]]` link used for property lookup — that chain is how inheritance works in JS. Use `Object.create` or constructor `prototype` when you need classic prototype-style inheritance, and understand `hasOwnProperty` vs inherited props to avoid bugs.

```javascript
// Constructor + prototype: shared methods live on .prototype
function Animal(name) {
  this.name = name;
}
Animal.prototype.speak = function () {
  return `${this.name} makes a sound`;
};

// Subclass via Object.create
function Dog(name) {
  Animal.call(this, name);          // run parent constructor
}
Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog;    // fix the constructor pointer
Dog.prototype.speak = function () {
  return `${this.name} barks`;
};

const d = new Dog("Rex");
console.log(d.speak());                          // "Rex barks"
console.log(d instanceof Dog);                   // true
console.log(d instanceof Animal);                // true — chain intact
console.log(Object.hasOwn(d, "name"));           // true (own)
console.log(Object.hasOwn(d, "speak"));          // false (inherited)
console.log("speak" in d);                       // true (own or inherited)

// Reusable inheritance helper
function inherits(child, parent) {
  child.prototype = Object.create(parent.prototype);
  child.prototype.constructor = child;
}
function Cat(name) {
  Animal.call(this, name);
}
inherits(Cat, Animal);
const cat = new Cat("Momo");
console.log(cat.speak());                        // "Momo makes a sound"

// Object.create with a custom prototype object
const petProto = { greet() { return `meow, I am ${this.name}`; } };
const kitten = Object.create(petProto);
kitten.name = "Zoe";
console.log(kitten.greet());                     // "meow, I am Zoe"
```

Gotchas:
- Always reassign `.constructor` after `Object.create(Animal.prototype)` or `d.constructor` points at the parent.
- Setting `Dog.prototype = new Animal()` runs the parent constructor with side effects; prefer `Object.create(Animal.prototype)`.
- Arrow functions can't be used as constructors (`new` throws). Use `function` or class.
- `for...in` walks inherited enumerable props — use `Object.hasOwn()`/`Object.keys()` to filter.
- Never mutate `Object.prototype` directly; it changes every object and enables prototype-pollution attacks.
- Class `extends` is sugar over this, but `super` in classes handles parent constructors/this binding correctly — don't hand-roll it when a class fits.
