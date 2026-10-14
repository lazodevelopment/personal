"""patch_vendor_couple_view.py - JC-LAZO-VIEWSWITCH-1014-001: "Couple view" moves into the desk menu.
The link sat loose between the mode switch and the cards on every vendor's Today (phone and desktop). It exists so
a store reviewer can reach the couple side; it now lives in the gold desk button's menu, after Account, where all
the dashboard's navigation is - findable by a reviewer, out of everyone else's way.
Applied by patch_june_hero_dashboards.py to Vendor_master_v189 (imported, not run alone).
"""


def apply_couple_view(v, rep):
    block_phone = """                const SizedBox(height: 10),
                // JC-LAZO-VIEWSWITCH-0917-001: back to the couple side.
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () async {
                      await _markViewSwitch();
                      if (mounted) {
                        context.goNamed('CoupleHome');
                      }
                    },
                    icon: const Icon(Icons.favorite_rounded, size: 16),
                    label: const Text('Couple view'),
                    style: TextButton.styleFrom(foregroundColor: _lzFg(plum)),
                  ),
                ),
                const SizedBox(height: 16),
"""
    v = rep(v, block_phone, "                const SizedBox(height: 16),\n", "couple view phone")
    block_wide = """                  const SizedBox(height: 10),
                  // JC-LAZO-VIEWSWITCH-0917-001: back to the couple side.
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () async {
                        await _markViewSwitch();
                        if (mounted) {
                          context.goNamed('CoupleHome');
                        }
                      },
                      icon: const Icon(Icons.favorite_rounded, size: 16),
                      label: const Text('Couple view'),
                      style: TextButton.styleFrom(foregroundColor: _lzFg(plum)),
                    ),
                  ),
                  const SizedBox(height: 16),
"""
    v = rep(v, block_wide, "                  const SizedBox(height: 16),\n", "couple view wide")
    acct = """        'Account',
        Icons.person_rounded,
        () => setState(() {
              _showInbox = false;
              _editingProfile = false;
              _showAccount = true;
              _acctSeeded = false;
            })
      ],
    ];"""
    v = rep(v, acct, """        'Account',
        Icons.person_rounded,
        () => setState(() {
              _showInbox = false;
              _editingProfile = false;
              _showAccount = true;
              _acctSeeded = false;
            })
      ],
      // JC-LAZO-VIEWSWITCH-1014-001: the couple side, from the desk (it used to sit loose under the mode switch)
      <dynamic>[
        'Couple view',
        Icons.favorite_rounded,
        () async {
          await _markViewSwitch();
          if (mounted) context.goNamed('CoupleHome');
        }
      ],
    ];""", "couple view in desk")
    return v
