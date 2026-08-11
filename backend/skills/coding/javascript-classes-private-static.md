---
lang: javascript
keywords: class, private fields, static method, getter, setter, extends, super, public class fields, static blocks, brand check
---

# Classes: private fields & static members

ES2022 classes support real `#private` fields (hard privacy, enforced by the engine) and `static` members shared by the class, not instances. Reach for classes when you want constructor-time setup, encapsulation, and inheritance in one declarative shape.

```javascript
class BankAccount {
  // private field — only usable inside the class body
  #balance = 0;
  static #minBalance = -100;         // private static field
  static instances = 0;              // public static field

  constructor(owner, opening = 0) {
    this.owner = owner;              // public field
    this.#balance = opening;
    BankAccount.instances++;
  }

  get balance() { return this.#balance; }
  set balance(v) {
    if (typeof v !== "number") throw new TypeError("balance must be a number");
    if (v < BankAccount.#minBalance) throw new RangeError("overdraft limit");
    this.#balance = v;
  }

  deposit(amount) {
    if (amount <= 0) throw new RangeError("amount must be positive");
    this.#balance += amount;
    return this.#balance;
  }

  static totalAccounts() {
    return BankAccount.instances;
  }
}

const acct = new BankAccount("Ada", 100);
acct.deposit(50);
console.log(acct.balance);                       // 150 (via getter)
acct.balance = 200;
console.log(BankAccount.totalAccounts());        // 1
console.log(Object.keys(acct));                  // ["owner"] — #balance invisible
// acct.#balance → SyntaxError outside the class

// Inheritance: #fields are NOT inherited; subclasses use public API
class Savings extends BankAccount {
  constructor(owner, opening, rate) {
    super(owner, opening);
    this.rate = rate;
  }
  applyInterest() { this.deposit(this.balance * this.rate); }
}
const s = new Savings("Bob", 1000, 0.01);
s.applyInterest();
console.log(s.balance);                          // 1010
```

Gotchas:
- `#field` must be declared in the class body before use; accessed only from inside the class — not even subclasses.
- Private fields are invisible to `JSON.stringify` and `Object.keys` — don't use them for state you must serialize.
- `static` fields and blocks run in source order at class-definition time; referencing another static before its initialization yields `undefined`.
- Getter/setter pair on the same name is required (`get balance` needs `set balance`); classes are strict, so a write with only a getter throws TypeError.
- `super()` must be called before touching `this` in a subclass constructor, or you get a ReferenceError.
- Private brand check throws on instances of the wrong class — use it as validation instead of duck-typing.
