from .errors import ValidationError


class Validator(object):
    def __call__(self, value):
        pass


class NullValidator(Validator):
    def __call__(self, value):
        pass


class IntegerValidator(Validator):
    def __call__(self, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError("Value {} is not an integer".format(value))


class Type(object):
    def __init__(self, value, validator=NullValidator()):
        assert isinstance(validator, Validator)
        self.validator = validator
        self.val = None
        self.set_value(value)

    def value(self):
        return self.val

    def set_value(self, value):
        self.validate(value)
        self.val = value

    def validate(self, val):
        self.validator(val)

    def __str__(self):
        return str(self.val)

    def __repr__(self):
        return repr(self.val)

    def __eq__(self, other):
        if isinstance(other, Type):
            return self.val == other.val
        else:
            return self.val == other

    def __ne__(self, other):
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented


class Any(Type):
    def __init__(self, value):
        super(Any, self).__init__(value=value, validator=NullValidator())

        super(Any, self).__init__(value=value, validator=NullValidator())


class Integer(Type):
    def __init__(self, n):
        super(Integer, self).__init__(value=n, validator=IntegerValidator())
