"""Small, dependency-free evaluator for COBRA-style GPR rules.

The grammar supported by SBML gene-protein-reaction rules is boolean:
gene identifiers combined with AND, OR and parentheses.  A reaction remains
functional while its complete rule evaluates to True under the selected gene
knockouts.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\(|\)|\bAND\b|\bOR\b|[A-Za-z0-9_.:-]+", re.IGNORECASE)


class _GPRParser:
    def __init__(self, tokens, knocked_out_genes):
        self.tokens = list(tokens)
        self.position = 0
        self.knocked_out = {str(gene_id).strip().lower() for gene_id in knocked_out_genes}

    def _peek(self):
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _take(self):
        token = self._peek()
        if token is not None:
            self.position += 1
        return token

    def parse(self):
        value = self._parse_or()
        if self._peek() is not None:
            raise ValueError(f"Unexpected token in GPR rule: {self._peek()}")
        return bool(value)

    def _parse_or(self):
        value = self._parse_and()
        while str(self._peek()).lower() == 'or':
            self._take()
            rhs = self._parse_and()
            value = bool(value or rhs)
        return value

    def _parse_and(self):
        value = self._parse_factor()
        while str(self._peek()).lower() == 'and':
            self._take()
            rhs = self._parse_factor()
            value = bool(value and rhs)
        return value

    def _parse_factor(self):
        token = self._take()
        if token is None:
            raise ValueError('Unexpected end of GPR rule.')

        if token == '(':
            value = self._parse_or()
            if self._take() != ')':
                raise ValueError('Unbalanced parentheses in GPR rule.')
            return value

        lowered = token.lower()
        if lowered in {'and', 'or'} or token == ')':
            raise ValueError(f'Unexpected token in GPR rule: {token}')

        return lowered not in self.knocked_out


def evaluate_gpr_rule(rule, knocked_out_genes):
    """Return whether a reaction GPR remains functional after gene knockouts."""
    text = str(rule or '').strip()
    if not text:
        return True

    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return True
    return _GPRParser(tokens, knocked_out_genes).parse()


def disabled_reaction_ids(metabolic_model, knocked_out_genes):
    """Return reaction ids whose complete GPR becomes false.

    The model is only read; neither gene state nor reaction bounds are mutated.
    This makes the function safe to use for repeated simulations and concurrent
    request handling at the GPR-evaluation level.
    """
    knocked_out = {str(gene_id).strip() for gene_id in knocked_out_genes if str(gene_id).strip()}
    if not knocked_out:
        return []

    disabled = []
    for reaction in metabolic_model.reactions:
        rule = str(getattr(reaction, 'gene_reaction_rule', '') or '').strip()
        if not rule:
            continue
        if not evaluate_gpr_rule(rule, knocked_out):
            disabled.append(str(reaction.id))
    return disabled
