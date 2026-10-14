            // v190: Add your business in three short steps - Business,
            // Services, Verify. Continue is always tappable and says what is
            // missing instead of greying out.
            final List<Widget> chips = <Widget>[];
            for (int i = 0; i < _catIds.length; i++) {
              final String id = _catIds[i];
              chips.add(_onbChip(
                  label: _catNames[i],
                  selected: picked.contains(id),
                  onTap: busy
                      ? null
                      : () {
                          setD(() {
                            if (picked.contains(id)) {
                              picked.remove(id);
                            } else {
                              picked.add(id);
                            }
                            formError = null;
                          });
                        }));
            }
            const List<String> heardOptions = <String>[
              'Google search',
              'ChatGPT or another AI assistant',
              'Instagram',
              'Facebook',
              'TikTok',
              'A couple or client',
              'Another vendor',
              'Zola, The Knot or WeddingWire',
              'An email or text from Lazo',
              'Word of mouth',
              'Other',
            ];
            final List<DropdownMenuItem<String>> heardItems = heardOptions
                .map((String o) =>
                    DropdownMenuItem<String>(value: o, child: Text(o)))
                .toList();

            String? stepError() {
              if (step == 0) {
                if (nameC.text.trim().length < 2) {
                  return 'Add your business name as couples know it.';
                }
                if (phoneC.text.replaceAll(RegExp(r'[^0-9]'), '').length < 10) {
                  return 'Add a business phone number with its area code.';
                }
              } else if (step == 1) {
                if (picked.isEmpty) {
                  return 'Pick at least one thing you do.';
                }
                if (heardAbout == null) {
                  return 'Tell us how you heard about Lazo.';
                }
              } else if (pb == null) {
                return 'Attach a document so we can verify your business.';
              }
              return null;
            }

            void next() {
              final String? err = stepError();
              if (err != null) {
                setD(() {
                  formError = err;
                });
                return;
              }
              if (step < 2) {
                setD(() {
                  step = step + 1;
                  formError = null;
                });
                return;
              }
              doSubmit();
            }

            final String metroName = _metroLabel(_claimMetro);
            final String bizName = nameC.text.trim();
            final List<Widget> body;
            if (step == 0) {
              body = <Widget>[
                _onbLabel('YOUR BUSINESS'),
                const SizedBox(height: 12),
                TextField(
                    controller: nameC,
                    enabled: !busy,
                    onChanged: (String s) {
                      setD(() {
                        formError = null;
                      });
                    },
                    textCapitalization: TextCapitalization.words,
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Business name',
                        icon: Icons.storefront_rounded,
                        helper: 'Exactly as couples know it.')),
                const SizedBox(height: 12),
                TextField(
                    controller: phoneC,
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
                    decoration:
                        _onbDeco('Business phone', icon: Icons.phone_rounded)),
                const SizedBox(height: 12),
                TextField(
                    controller: webC,
                    enabled: !busy,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Website (optional)',
                        icon: Icons.language_rounded,
                        helper: 'Double-check the spelling. Couples tap it.')),
                const SizedBox(height: 12),
                TextField(
                    controller: legalEntityC,
                    enabled: !busy,
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _onbDeco('Legal entity (optional)',
                        icon: Icons.account_balance_rounded,
                        helper:
                            'The LLC or company on your license, if it differs.')),
                const SizedBox(height: 16),
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Icon(Icons.place_rounded, size: 16, color: _lzFg(muted)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                        'Listed in ' +
                            (metroName.isEmpty ? 'your city' : metroName) +
                            '. You can change your service area later.',
                        style: TextStyle(
                            color: _lzFg(muted), fontSize: 12, height: 1.4)),
                  ),
                ]),
                _onbError(formError),
                const SizedBox(height: 8),
              ];
            } else if (step == 1) {
              body = <Widget>[
                _onbLabel('WHAT DO YOU DO?'),
                const SizedBox(height: 4),
                Text('Pick everything you offer. Couples search by these.',
                    style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                const SizedBox(height: 14),
                Wrap(spacing: 8, runSpacing: 8, children: chips),
                const SizedBox(height: 24),
                _onbLabel('ONE LAST QUESTION'),
                const SizedBox(height: 12),
                // JC-LAZO-VDASH-1012-188: where they came from
                DropdownButtonFormField<String>(
                  value: heardAbout,
                  isExpanded: true,
                  decoration: _onbDeco('How did you hear about Lazo?',
                      icon: Icons.campaign_rounded),
                  style: TextStyle(
                      color: _lzFg(ink),
                      fontSize: 15,
                      fontWeight: FontWeight.w500),
                  dropdownColor: _lzBg(ivory),
                  borderRadius: BorderRadius.circular(16),
                  items: heardItems,
                  onChanged: busy
                      ? null
                      : (String? val) {
                          setD(() {
                            heardAbout = val;
                            formError = null;
                          });
                        },
                ),
                if (heardAbout == 'Other') ...<Widget>[
                  const SizedBox(height: 12),
                  TextField(
                      controller: heardOtherC,
                      enabled: !busy,
                      cursorColor: _lzFg(plum),
                      style: TextStyle(color: _lzFg(ink), fontSize: 15),
                      decoration: _onbDeco('Where exactly? (optional)')),
                ],
                _onbError(formError),
                const SizedBox(height: 8),
              ];
            } else {
              final List<String> catLabels = <String>[];
              for (final String id in picked) {
                final int ci = _catIds.indexOf(id);
                if (ci >= 0) {
                  catLabels.add(_catNames[ci]);
                }
              }
              body = <Widget>[
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: _lzBg(const Color(0xFFFBF5EA)),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: _lzLine(goldLine)),
                  ),
                  child: Row(children: <Widget>[
                    _onbMonogram(bizName, size: 46),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(bizName,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: _serif(
                                  size: 20,
                                  weight: FontWeight.w700,
                                  height: 1.1)),
                          const SizedBox(height: 3),
                          Text(
                              <String>[
                                catLabels.join(', '),
                                if (metroName.isNotEmpty) metroName,
                              ].where((String s) => s.isNotEmpty).join(' · '),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                  color: _lzFg(muted),
                                  fontSize: 12.5,
                                  height: 1.35)),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: _h(busy
                          ? null
                          : () {
                              setD(() {
                                step = 0;
                                formError = null;
                              });
                            }),
                      child: Text('Edit',
                          style: TextStyle(
                              color: _lzFg(plum), fontWeight: FontWeight.w700)),
                    ),
                  ]),
                ),
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
              ];
            }

            return _onbSheet(
              ctx: ctx2,
              icon: Icons.add_business_rounded,
              eyebrow: 'JOIN LAZO · FREE FOREVER',
              title: (step == 0 || bizName.isEmpty) ? 'Add your business' : bizName,
              subtitle: step == 0
                  ? 'Three short steps. We verify every business so couples can trust every profile.'
                  : '',
              step: step,
              steps: const <String>['Business', 'Services', 'Verify'],
              body: body,
              footer: _onbFooter(
                backLabel: step == 0 ? 'Cancel' : 'Back',
                onBack: busy
                    ? null
                    : () {
                        if (step == 0) {
                          Navigator.pop(ctx2, false);
                        } else {
                          setD(() {
                            step = step - 1;
                            formError = null;
                          });
                        }
                      },
                primary: _onbPrimary(
                    label: step < 2 ? 'Continue' : 'Submit for review',
                    busy: busy,
                    busyLabel: 'Submitting…',
                    icon: step < 2
                        ? Icons.arrow_forward_rounded
                        : Icons.check_rounded,
                    onPressed: next),
              ),
            );
          },
        );
      },
    );

