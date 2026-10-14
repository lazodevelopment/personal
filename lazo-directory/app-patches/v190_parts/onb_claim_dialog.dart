            // v190: the claim sheet. Who you are, how couples reach you, the proof.
            final List<Widget> roleChips = <Widget>[];
            for (final String r in <String>[
              'Owner',
              'Manager',
              'Authorized representative'
            ]) {
              roleChips.add(_onbChip(
                  label: r,
                  selected: claimantRole == r,
                  onTap: busy
                      ? null
                      : () {
                          setD(() {
                            claimantRole = r;
                          });
                        }));
            }
            final String where =
                v['address'] == null ? '' : v['address'].toString().trim();
            return _onbSheet(
              ctx: ctx2,
              icon: Icons.verified_user_rounded,
              eyebrow: 'STEP 2 · VERIFY OWNERSHIP',
              title: name,
              subtitle: (where.isEmpty ? '' : where + '\n') +
                  'Lazo verifies every business so couples can trust every profile. This takes about a minute.',
              body: <Widget>[
                _onbLabel('YOUR ROLE'),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: roleChips),
                const SizedBox(height: 22),
                _onbLabel('HOW COUPLES REACH YOU'),
                const SizedBox(height: 12),
                TextField(
                    controller: bizEmailC,
                    enabled: !busy,
                    onChanged: (String s) {
                      setD(() {
                        formError = null;
                      });
                    },
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const <String>[AutofillHints.email],
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Business email',
                        icon: Icons.alternate_email_rounded,
                        helper:
                            'An address on your website’s domain verifies fastest.')),
                const SizedBox(height: 12),
                TextField(
                    controller: bizPhoneC,
                    enabled: !busy,
                    onChanged: (String s) {
                      setD(() {
                        formError = null;
                      });
                    },
                    keyboardType: TextInputType.phone,
                    autofillHints: const <String>[AutofillHints.telephoneNumber],
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Business phone',
                        icon: Icons.phone_rounded,
                        helper: 'The number on your public listing.')),
                const SizedBox(height: 12),
                TextField(
                    controller: legalEntityC,
                    enabled: !busy,
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Legal entity (optional)',
                        icon: Icons.account_balance_rounded,
                        helper:
                            'The LLC or company on your license, if it differs from the name above.')),
                const SizedBox(height: 22),
                _onbLabel('PROOF OF OWNERSHIP'),
                const SizedBox(height: 12),
                _onbProof(
                    bytes: pb,
                    isPdf: proofIsPdf,
                    fileName: proofName,
                    busy: busy,
                    onPick: pickProof),
                _onbError(formError),
                const SizedBox(height: 8),
              ],
              footer: _onbFooter(
                backLabel: 'Cancel',
                onBack: busy
                    ? null
                    : () {
                        Navigator.pop(ctx2, false);
                      },
                // always tappable: doSubmit says what is missing
                primary: _onbPrimary(
                    label: 'Submit for verification',
                    busy: busy,
                    busyLabel: 'Submitting…',
                    icon: Icons.arrow_forward_rounded,
                    onPressed: doSubmit),
              ),
            );
          },
        );
      },
    );

