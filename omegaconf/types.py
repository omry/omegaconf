class ValidationError(Exception):
    """
    Thrown when a value fails validation
    """


class Validator(object):
    def __call__(self, t):
        pass


class NullValidator(Validator):
    def __call__(self, t):
        pass


class IntegerValidator(Validator):
    def __call__(self, t):
        try:
            int(t.value())
        except ValueError:
            raise ValidationError("Value {} is not an integer".format(t.value))


class Type(object):
    def __init__(self, value, validator=NullValidator()):
        assert isinstance(validator, Validator)
        self.validator = validator
        self.val = value
        self.validate()

    def value(self):
        return self.val

    def validate(self):
        self.validator(self)

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
        super(Any, self).__init__(value=n, validator=IntegerValidator())
