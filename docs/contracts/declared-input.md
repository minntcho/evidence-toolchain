# Declared Input 계약

`DeclaredInput`은 caller가 evidence와 비교하려는 value, field, 또는 question을 나타냅니다.

구현이 evolve하면서 이름은 바뀔 수 있지만 책임은 안정적으로 유지되어야 합니다. 이것은 evidence가 support, contradict, fail to find, uncertain으로 남길 수 있는 caller-side value 또는 request입니다.

## 포함할 수 있는 것

Declared input은 다음을 담을 수 있습니다.

- input id
- requested field name
- declared value
- declared unit
- declared period 또는 date
- source system metadata
- optional matching hint
- optional required evidence type

Caller가 open-ended extraction만 원할 때는 declared input이 없을 수 있습니다.

## 해서는 안 되는 일

Declared input은 final Downstream approval을 담으면 안 됩니다.

Value가 committed되었는지, policy-sufficient한지, legally accepted인지, ready for publication인지 말하면 안 됩니다. 그런 state는 Downstream system에 속합니다.

## Evidence와의 관계

Evidence는 declared input을 support, contradict, miss, uncertain으로 남길 수 있습니다. Declared input 자체는 evidence가 아닙니다. Evidence와 대조되는 checked value입니다.
